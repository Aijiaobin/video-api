import httpx
import re
import json
from typing import Optional, List, Dict
from ..models.models import ShareLink, ShareFile, Sharer
from sqlalchemy.orm import Session
from .title_cleaner import title_cleaner, file_name_cleaner


def clean_share_url(raw_url: str) -> str:
    """
    清理分享链接，提取纯净的URL

    示例:
    输入: "复制这段内容后打开天翼云盘手机App，操作更方便哦！链接：https://cloud.189.cn/t/xxx（访问码：xxxx）"
    输出: "https://cloud.189.cn/t/xxx"
    """
    if not raw_url:
        return ""

    # 尝试提取 URL - 只匹配到分享码结束
    # 格式1: https://cloud.189.cn/t/xxxxx
    # 格式2: https://cloud.189.cn/web/share?code=xxxxx
    url_patterns = [
        r'https?://cloud\.189\.cn/t/([a-zA-Z0-9]+)',
        r'https?://cloud\.189\.cn/web/share\?code=([a-zA-Z0-9]+)',
        r'https?://h5\.cloud\.189\.cn/share\.html#/t/([a-zA-Z0-9]+)',
    ]

    for pattern in url_patterns:
        match = re.search(pattern, raw_url)
        if match:
            # 返回完整匹配的URL部分
            return match.group(0)

    return raw_url.strip()


def extract_password_from_text(raw_text: str) -> str:
    """
    从文本中提取访问码/提取码

    示例:
    输入: "https://cloud.189.cn/t/xxx（访问码：abcd）"
    输出: "abcd"
    """
    if not raw_text:
        return ""

    # 匹配访问码的几种常见格式
    password_patterns = [
        r'[（(]访问码[：:]\s*([a-zA-Z0-9]{4})[)）]',  # （访问码：xxxx）
        r'[（(]提取码[：:]\s*([a-zA-Z0-9]{4})[)）]',  # （提取码：xxxx）
        r'访问码[：:]\s*([a-zA-Z0-9]{4})',           # 访问码：xxxx
        r'提取码[：:]\s*([a-zA-Z0-9]{4})',           # 提取码：xxxx
    ]

    for pattern in password_patterns:
        match = re.search(pattern, raw_text)
        if match:
            return match.group(1)

    return ""


class TianYiShareParser:
    """天翼云盘分享链接解析器"""

    BASE_URL = "https://cloud.189.cn"

    async def parse_share(self, share_url: str, password: str = None) -> Optional[Dict]:
        """
        解析天翼云盘分享链接
        返回: {
            raw_title: 原始标题,
            clean_title: 清洗后标题,
            share_type: 分享类型,
            share_code: 分享码,
            sharer_info: {sharer_id, nickname, avatar_url},
            files: [{file_id, file_name, clean_name, file_size, is_directory, file_type, ...}]
        }
        """
        # 清理URL
        clean_url = clean_share_url(share_url)

        # 提取分享码
        share_code = self._extract_share_code(clean_url)
        if not share_code:
            return None

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                # 1. 获取分享信息 (使用 V2 API)
                share_info = await self._get_share_info_v2(client, share_code, password)
                if not share_info:
                    return None

                # 2. 获取文件列表
                share_id = share_info.get("shareId", "")
                file_id = share_info.get("fileId", "-11")
                is_folder = share_info.get("isFolder", False)
                share_mode = share_info.get("shareMode", 0)

                files = []
                if is_folder:
                    files = await self._get_file_list_v2(client, share_id, file_id, share_mode, password)
                else:
                    # 单文件分享
                    file_name = share_info.get("fileName", "")
                    file_info = file_name_cleaner.parse(file_name)
                    files = [{
                        "file_id": file_id,
                        "file_name": file_name,
                        "clean_name": file_info["clean_name"],
                        "file_size": share_info.get("fileSize", 0),
                        "is_directory": False,
                        "file_type": file_info["file_type"],
                        "season_number": file_info["season_number"],
                        "episode_number": file_info["episode_number"],
                        "resolution": file_info["resolution"],
                        "video_codec": file_info["video_codec"],
                        "audio_codec": file_info["audio_codec"]
                    }]

                # 3. 处理标题
                raw_title = share_info.get("fileName", "未知分享")
                clean_result = title_cleaner.clean(raw_title)

                # 4. 根据文件列表智能判断分享类型
                # 注意：有些分享根目录只有子文件夹（例如按季/按集分文件夹），
                # 此时根目录可能没有 video 文件，需做浅层探测避免误判为 movie。
                files_for_type = files
                if is_folder:
                    root_video_files = [f for f in files if f.get("file_type") == "video"]
                    root_folders = [f for f in files if f.get("is_directory")]

                    if not root_video_files and root_folders:
                        sampled_files: List[Dict] = []
                        # 只做浅层扫描，避免请求过多
                        for folder in root_folders[:10]:
                            folder_id = folder.get("file_id")
                            if not folder_id:
                                continue
                            sampled_files.extend(
                                await self._get_file_list_v2(client, share_id, folder_id, share_mode, password)
                            )
                            # 发现足够多的视频后提前结束
                            if len([f for f in sampled_files if f.get("file_type") == "video"]) >= 4:
                                break

                        files_for_type = files + sampled_files

                share_type = self._detect_share_type_by_files(files_for_type, clean_result.share_type)

                # 5. 获取分享人信息
                sharer_info = {
                    "sharer_id": share_info.get("shareUserId", ""),
                    "nickname": share_info.get("shareUserNickName", ""),
                    "avatar_url": share_info.get("shareUserHeadUrl", "")
                }

                return {
                    "raw_title": raw_title,
                    "clean_title": clean_result.clean_title,
                    "share_type": share_type,
                    "year": clean_result.year,
                    "season_number": clean_result.season_number,
                    "resolution": clean_result.resolution,
                    "share_code": share_code,
                    "share_id": share_id,
                    "sharer_info": sharer_info,
                    "file_count": len(files),
                    "files": files
                }
        except Exception as e:
            print(f"Parse share failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _detect_share_type_by_files(self, files: list, title_type: str) -> str:
        """
        根据文件列表智能判断分享类型

        规则:
        1. 如果标题已识别为 movie_collection，保持不变
        2. 如果有多个视频文件且包含集号信息，判定为 tv
        3. 如果只有1个视频文件，判定为 movie
        4. 其他情况使用标题判断的结果
        """
        # 如果标题已识别为合集，保持不变
        if title_type == "movie_collection":
            return "movie_collection"

        # 统计视频文件和有集号的文件
        video_files = [f for f in files if f.get("file_type") == "video"]
        files_with_episode = [f for f in video_files if f.get("episode_number") is not None]

        # 根目录(或浅层采样)只有子文件夹时，仍然可能是 TV
        # 只要存在多个文件夹且没有明显的“多电影合集”信号，就更倾向 tv
        folder_count = len([f for f in files if f.get("is_directory")])

        # 如果有多个视频文件且有集号信息，判定为 tv
        if len(video_files) > 1 and len(files_with_episode) > 0:
            return "tv"

        # 如果只有1个视频文件，判定为 movie
        if len(video_files) == 1:
            return "movie"

        # 多视频但没有集号：
        # - 如果来源于子文件夹（folder_count > 0），更可能是剧集（按季/按集分目录）
        # - 如果全在根目录且数量很多，才更像电影合集
        if len(video_files) > 1 and len(files_with_episode) == 0 and folder_count > 0:
            return "tv"

        # 如果有多个视频文件但没有集号，可能是电影合集或多版本
        if len(video_files) > 3 and len(files_with_episode) == 0:
            return "movie_collection"

        # 如果没有视频文件，但有多个文件夹：更可能是剧集/番剧（按季/按集分文件夹）
        if len(video_files) == 0 and folder_count >= 2:
            # 标题如果明确是 movie_collection 则前面已返回
            # 这里优先判 tv，避免默认 movie
            return "tv"

        # 其他情况使用标题判断的结果
        return title_type

    def _extract_share_code(self, share_url: str) -> Optional[str]:
        """从分享链接提取分享码"""
        # https://cloud.189.cn/t/xxxxx
        # https://cloud.189.cn/web/share?code=xxxxx
        patterns = [
            r"cloud\.189\.cn/t/([a-zA-Z0-9]+)",
            r"cloud\.189\.cn/web/share\?code=([a-zA-Z0-9]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, share_url)
            if match:
                return match.group(1)
        return None
    
    async def _get_share_info_v2(self, client: httpx.AsyncClient, share_code: str, password: str = None) -> Optional[Dict]:
        """获取分享基本信息 - 使用 V2 API (返回 JSON)"""
        url = f"{self.BASE_URL}/api/open/share/getShareInfoByCodeV2.action"
        params = {"shareCode": share_code}

        headers = {
            "Accept": "application/json;charset=UTF-8",
            "Referer": f"{self.BASE_URL}/"
        }

        resp = await client.get(url, params=params, headers=headers)
        print(f"getShareInfoByCodeV2 response: {resp.text[:500]}")

        if resp.status_code != 200:
            print(f"getShareInfoByCodeV2 failed: {resp.status_code}")
            return None

        try:
            data = resp.json()
            if data.get("res_code") and data.get("res_code") != 0:
                print(f"getShareInfoByCodeV2 error: {data.get('res_message')}")
                return None

            # 获取分享人信息 (在 creator 对象中)
            creator = data.get("creator", {})
            share_mode = data.get("shareMode", 0)
            share_id = str(data.get("shareId", ""))

            # 如果是加密分享 (shareMode == 1)，需要验证访问码
            if share_mode == 1:
                if not password:
                    print("加密分享需要访问码")
                    return None
                # 验证访问码并获取正确的 shareId
                check_result = await self._check_access_code(client, share_code, password)
                if not check_result:
                    print("访问码验证失败")
                    return None
                share_id = check_result.get("shareId", share_id)
                print(f"加密分享验证成功，shareId: {share_id}")

            return {
                "fileName": data.get("fileName", ""),
                "fileId": str(data.get("fileId", "")),
                "fileSize": data.get("fileSize", 0),
                "isFolder": data.get("isFolder") == 1,
                "shareId": share_id,
                "shareMode": share_mode,
                # 分享人信息 (从 creator 对象提取)
                "shareUserId": str(creator.get("ownerAccount", "")),
                "shareUserNickName": creator.get("nickName", ""),
                "shareUserHeadUrl": creator.get("iconURL", ""),
            }
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return None

    async def _check_access_code(self, client: httpx.AsyncClient, share_code: str, access_code: str) -> Optional[Dict]:
        """验证分享链接访问码"""
        import uuid
        url = f"{self.BASE_URL}/api/open/share/checkAccessCode.action"
        params = {
            "shareCode": share_code,
            "accessCode": access_code,
            "uuid": str(uuid.uuid4())
        }

        headers = {
            "Accept": "application/json;charset=UTF-8",
            "Referer": f"{self.BASE_URL}/"
        }

        resp = await client.get(url, params=params, headers=headers)
        print(f"checkAccessCode response: {resp.text[:500]}")

        if resp.status_code != 200:
            print(f"checkAccessCode failed: {resp.status_code}")
            return None

        try:
            data = resp.json()
            if data.get("res_code") and data.get("res_code") != 0:
                print(f"checkAccessCode error: {data.get('res_message')}")
                return None

            return {
                "shareId": str(data.get("shareId", ""))
            }
        except json.JSONDecodeError as e:
            print(f"JSON parse error in checkAccessCode: {e}")
            return None
    
    async def _get_file_list_v2(self, client: httpx.AsyncClient, share_id: str, file_id: str, share_mode: int = 0, password: str = None) -> List[Dict]:
        """获取分享文件列表 - 使用新 API"""
        url = f"{self.BASE_URL}/api/open/share/listShareDir.action"
        params = {
            "shareId": share_id,
            "fileId": file_id,
            "isFolder": "true",
            "orderBy": "lastOpTime",
            "descending": "true",
            "shareMode": share_mode,
            "pageNum": 1,
            "pageSize": 1000
        }
        if password:
            params["accessCode"] = password

        headers = {
            "Accept": "application/json;charset=UTF-8",
            "Referer": f"{self.BASE_URL}/"
        }

        resp = await client.get(url, params=params, headers=headers)
        print(f"listShareDir response: {resp.text[:500]}")

        if resp.status_code != 200:
            print(f"listShareDir failed: {resp.status_code}")
            return []

        files = []
        try:
            data = resp.json()
            file_list_ao = data.get("fileListAO", {})

            # 解析文件夹
            for item in file_list_ao.get("folderList", []):
                files.append({
                    "file_id": str(item.get("id", "")),
                    "file_name": item.get("name", ""),
                    "clean_name": item.get("name", ""),
                    "file_size": 0,
                    "is_directory": True,
                    "file_type": "other",
                    "season_number": None,
                    "episode_number": None,
                    "resolution": None,
                    "video_codec": None,
                    "audio_codec": None
                })

            # 解析文件
            for item in file_list_ao.get("fileList", []):
                file_name = item.get("name", "")
                file_info = file_name_cleaner.parse(file_name)
                files.append({
                    "file_id": str(item.get("id", "")),
                    "file_name": file_name,
                    "clean_name": file_info["clean_name"],
                    "file_size": item.get("size", 0),
                    "is_directory": False,
                    "file_type": file_info["file_type"],
                    "season_number": file_info["season_number"],
                    "episode_number": file_info["episode_number"],
                    "resolution": file_info["resolution"],
                    "video_codec": file_info["video_codec"],
                    "audio_codec": file_info["audio_codec"]
                })

        except json.JSONDecodeError as e:
            print(f"JSON parse error in listShareDir: {e}")

        return files


tianyi_parser = TianYiShareParser()
