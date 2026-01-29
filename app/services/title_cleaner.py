"""
标题清洗器 - 从网盘分享标题中提取干净的影视名称
"""
import re
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class CleanResult:
    """清洗结果"""
    clean_title: str  # 清洗后的标题
    share_type: str  # tv, movie, movie_collection
    year: Optional[int] = None  # 提取的年份
    season_number: Optional[int] = None  # 提取的季号
    resolution: Optional[str] = None  # 分辨率
    tmdb_id: Optional[int] = None  # 提取的 TMDB ID
    extra_info: Optional[Dict] = None  # 其他提取的信息


class TitleCleaner:
    """标题清洗器"""
    
    # 需要移除的模式（按优先级排序）
    REMOVE_PATTERNS = [
        # 网站标识和压制组标签（优先处理）
        r'〖[^〗]*〗',  # 匹配中文书名号内容（如：〖海绵小站 www.hmxz.org〗）
        r'〔[^〕]*〕',  # 匹配中文六角括号内容
        r'\[[^\]]*\]',  # 匹配所有方括号内容
        r'【[^】]*】',  # 匹配所有中文方括号内容
        r'《[^》]*》(?=\s)',  # 匹配书名号后跟空格的内容（如：《国漫》）

        # 发布组标识（在文件名末尾的 -组名 格式）
        r'-[A-Za-z0-9]+$',  # 匹配末尾的发布组标识（如：-ParkHD）
        r'@[A-Za-z0-9]+',  # 匹配 @ 开头的发布组标识

        # 分辨率和编码信息
        r'(?:Ma)?10p[_\-]?\d{3,4}p?',  # Ma10p_2160p
        r'\d{1,2}bit',  # 10bit, 8bit（位深信息）
        r'\d{3,4}[pP]',  # 1080p, 2160p, 720P
        r'4[kK]',  # 4K, 4k
        r'(?:UHD|FHD|HD|SD)(?![a-zA-Z])',  # UHD/FHD/HD/SD 但不匹配单词中的
        r'(?:HEVC|AVC|H\.?264|H\.?265|x264|x265|AV1)',
        r'(?:HDR10\+|HDR10|HDR|DV|Dolby\s*Vision)',  # HDR10+ 必须在 HDR 之前匹配
        r'(?:REMUX|WEB-?DL|WEBRip|BluRay|BDRip|DVDRip|HDTV)',
        r'(?:DTS[\d\.\-]*(?:HD)?(?:\.MA)?|AAC[\d\.]*|FLAC|AC3|TrueHD|Atmos|DDP[\d\.]*)',  # 音频编码（增强匹配 DTS-HD.MA）
        r'(?:5\.1|7\.1|2\.0)',  # 声道信息
        r'HQ',  # 高质量标记
        r'\d+帧',  # 60帧
        r'\d+fps',  # 60fps

        # 文件大小
        r'\d+(?:\.\d+)?\s*[TGMK]B',  # 1.5GB, 339G
        r'\d+[TGMK](?![a-zA-Z])',  # 339G

        # 集数信息（保留季信息用于判断类型）
        r'全\d+集',
        r'共\d+集',
        r'完结',
        r'更新至.*',

        # 附加说明
        r'附带.*',
        r'高码',
        r'纯银版',
        r'整轨',
        r'内嵌.*字.*',  # 内嵌简中硬字
        r'内封.*',
        r'外挂.*',
        r'简[中繁]',
        r'繁[中简]',
        r'中[英日韩]',
        r'双语',
        r'国[语粤]',
        r'粤语',

        # 括号内的年份后的内容 如 (2026)后面的4K
        r'(?<=\d{4}[)）])\s*4[kK]',

        # 英文标题后缀（通常是技术信息）
        r'\.(?:Chronicles|Story|Movie|Film|Series)\..*$',
    ]
    
    # 序号前缀模式
    PREFIX_PATTERNS = [
        r'^\d+[\.\、\-\s]+',  # 44. 或 44、 或 44-
        r'^[#＃]\d+\s*',  # #44
        r'^《[^》]*》\s*',  # 《国漫》
        r'^【[^】]*】\s*',  # 【动漫】
        r'^\[[^\]]*\]\s*',  # [动漫]
        r'^[A-Z](?=[^\w]|[A-Z]?[\u4e00-\u9fa5])',  # 单个大写字母开头（如 D斗罗）
    ]
    
    # 季号提取模式
    SEASON_PATTERNS = [
        r'第([一二三四五六七八九十\d]+)季',
        r'[Ss]eason\s*(\d+)',
        r'[Ss](\d+)',
    ]
    
    # 年份提取模式
    YEAR_PATTERNS = [
        r'[（\(](\d{4})[）\)]',  # (2026) 或 （2026）
        r'[\.\s](\d{4})[\.\s]',  # .2026. 或 空格2026空格
    ]

    # TMDB ID 提取模式
    TMDB_ID_PATTERNS = [
        r'\{tmdb[:\s\-]+(\d+)\}',      # {tmdb 156201} 或 {tmdb:156201} 或 {tmdb-156201}
        r'\[tmdb[:\s\-]+(\d+)\]',      # [tmdb 156201] 或 [tmdb:156201] 或 [tmdb-156201]
        r'\[tmdbid[=:\s\-]+(\d+)\]',   # [tmdbid=18674] 或 [tmdbid:18674] 或 [tmdbid-18674]
        r'\{tmdbid[=:\s\-]+(\d+)\}',   # {tmdbid=18674} 或 {tmdbid:18674} 或 {tmdbid-18674}
        r'tmdb[id]*[=:\s\-]+(\d+)',    # tmdb 156201 或 tmdbid=18674 或 tmdb-156201
    ]
    
    # 电影合集关键词
    COLLECTION_KEYWORDS = ['合集', '全集', '系列', '部电影', '部.电影']

    # TV 剧集关键词
    TV_KEYWORDS = ['第一季', '第二季', '第三季', '第四季', '第五季',
                   'Season', 'S01', 'S02', 'S03',
                   '连续剧', '电视剧', '番剧']
    
    def clean(self, raw_title: str) -> CleanResult:
        """
        清洗标题

        示例:
        - "44.散华礼弥 [SumiSora&MAI] [Ma10p_2160p]" -> "散华礼弥"
        - "剑来第二季4K高码附带第一季" -> "剑来"
        - "《国漫》仙逆" -> "仙逆"
        - "轧戏（2026）4K" -> "轧戏"
        - "张国荣电影合集（1980-2003）" -> "张国荣电影合集（1980-2003）" (保留，类型为movie_collection)
        - "滚滚红尘 {tmdb 156201}" -> "滚滚红尘" (提取 tmdb_id=156201)
        """
        if not raw_title:
            return CleanResult(clean_title="", share_type="movie")

        title = raw_title.strip()

        # 1. 提取 TMDB ID（在清洗前提取）
        tmdb_id = self._extract_tmdb_id(title)

        # 2. 判断分享类型
        share_type = self._detect_share_type(title)

        # 3. 提取年份
        year = self._extract_year(title)

        # 4. 提取季号
        season_number = self._extract_season_number(title)

        # 5. 提取分辨率
        resolution = self._extract_resolution(title)

        # 6. 如果是电影合集，保留原标题（只做基本清理）
        if share_type == "movie_collection":
            clean_title = self._basic_clean(title)
            return CleanResult(
                clean_title=clean_title,
                share_type=share_type,
                year=year,
                resolution=resolution,
                tmdb_id=tmdb_id
            )

        # 7. 清洗标题
        clean_title = self._deep_clean(title)

        return CleanResult(
            clean_title=clean_title,
            share_type=share_type,
            year=year,
            season_number=season_number,
            resolution=resolution,
            tmdb_id=tmdb_id
        )
    
    def _detect_share_type(self, title: str) -> str:
        """检测分享类型"""
        # 检查是否为电影合集
        for keyword in self.COLLECTION_KEYWORDS:
            if keyword in title:
                return "movie_collection"
        
        # 检查是否为 TV 剧集
        for keyword in self.TV_KEYWORDS:
            if keyword in title:
                return "tv"
        
        # 默认为电影
        return "movie"
    
    def _extract_year(self, title: str) -> Optional[int]:
        """提取年份"""
        for pattern in self.YEAR_PATTERNS:
            match = re.search(pattern, title)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2100:
                    return year
        return None

    def _extract_tmdb_id(self, title: str) -> Optional[int]:
        """提取 TMDB ID"""
        for pattern in self.TMDB_ID_PATTERNS:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def _extract_season_number(self, title: str) -> Optional[int]:
        """提取季号"""
        for pattern in self.SEASON_PATTERNS:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                season_str = match.group(1)
                return self._chinese_to_number(season_str)
        return None
    
    def _extract_resolution(self, title: str) -> Optional[str]:
        """提取分辨率"""
        if re.search(r'4[kK]|2160[pP]', title):
            return "4K"
        if re.search(r'1080[pP]|FHD', title, re.IGNORECASE):
            return "1080P"
        if re.search(r'720[pP]|HD', title, re.IGNORECASE):
            return "720P"
        return None
    
    def _basic_clean(self, title: str) -> str:
        """基本清理（用于电影合集）"""
        # 移除所有技术信息和年份信息
        result = title

        # 移除所有干扰模式
        for pattern in self.REMOVE_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # 移除年份范围（如 1972-1990）
        result = re.sub(r'\d{4}-\d{4}', '', result)

        # 移除点号分隔的单个年份
        result = re.sub(r'[\.\s]\d{4}[\.\s]', ' ', result)

        # 清理多余空格和符号
        result = re.sub(r'[\s_\-\.·]+', ' ', result)
        result = re.sub(r'^[\s\-_\.·&]+|[\s\-_\.·&]+$', '', result)

        return result.strip()
    
    def _deep_clean(self, title: str) -> str:
        """深度清洗（用于 TV 和单部电影）"""
        result = title

        # 0. 先移除 TMDB ID 标签（在其他清洗前）
        for pattern in self.TMDB_ID_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # 1. 处理特殊格式：如果标题包含中文名和英文名，优先提取中文名
        # 例如: "民国惊魂录[4K·高码·60帧].Chronicles.of..." -> "民国惊魂录"
        chinese_match = re.match(r'^([A-Z]?[\u4e00-\u9fa5]+[\d\u4e00-\u9fa5]*)', result)
        if chinese_match:
            chinese_part = chinese_match.group(1)
            # 如果中文部分后面紧跟着方括号或点号+英文，说明是中英文混合标题
            if re.search(r'^[A-Z]?[\u4e00-\u9fa5]+[\d\u4e00-\u9fa5]*[\[\[【\.]', result):
                # 提取纯中文标题部分
                result = chinese_part

        # 2. 移除序号前缀
        for pattern in self.PREFIX_PATTERNS:
            result = re.sub(pattern, '', result)

        # 3. 移除所有干扰模式
        for pattern in self.REMOVE_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # 4. 移除季号信息
        for pattern in self.SEASON_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        # 5. 移除年份（括号格式和点号分隔格式）
        result = re.sub(r'[（\(]\d{4}[）\)]', '', result)  # 移除 (2026) 或 （2026）
        result = re.sub(r'[\.\s]\d{4}[\.\s]', ' ', result)  # 移除 .1980. 或 空格1980空格

        # 6. 移除英文技术后缀（点号分隔的英文单词）
        # 例如: "民国惊魂录.Chronicles.of.the.Republic" -> "民国惊魂录"
        result = re.sub(r'\.[A-Za-z][A-Za-z0-9\.\-\']+$', '', result)

        # 7. 清理多余空格和符号
        result = re.sub(r'[\s_\-\.·]+', ' ', result)
        result = re.sub(r'^[\s\-_\.·&]+|[\s\-_\.·&]+$', '', result)

        # 8. 如果结果为空或太短，尝试从原标题提取
        if len(result.strip()) < 2:
            # 尝试提取第一个中文词组
            match = re.search(r'[\u4e00-\u9fa5]{2,}', title)
            if match:
                result = match.group(0)

        return result.strip()
    
    def _chinese_to_number(self, s: str) -> int:
        """中文数字转阿拉伯数字"""
        if s.isdigit():
            return int(s)
        
        chinese_nums = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '零': 0
        }
        
        if len(s) == 1:
            return chinese_nums.get(s, 1)
        
        # 处理 "十一" 到 "十九"
        if s.startswith('十'):
            if len(s) == 1:
                return 10
            return 10 + chinese_nums.get(s[1], 0)
        
        # 处理 "二十" 到 "九十九"
        if '十' in s:
            parts = s.split('十')
            tens = chinese_nums.get(parts[0], 0) * 10
            ones = chinese_nums.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return tens + ones
        
        return 1


# 文件名清洗器
class FileNameCleaner:
    """文件名清洗器 - 从文件名提取剧集信息"""
    
    # 剧集编号模式
    EPISODE_PATTERNS = [
        r'[Ss](\d+)[Ee](\d+)',  # S01E01
        r'[Ss](\d+)\.?[Ee]?[Pp]?(\d+)',  # S01.01 或 S01EP01
        r'第(\d+)季.*?第(\d+)集',  # 第1季第1集
        r'[Ee][Pp]?\.?(\d+)',  # EP01 或 E01 (只有集号)
        r'第(\d+)集',  # 第1集
        r'[\[\(](\d+)[\]\)]',  # [01] 或 (01)
        r'[\s\-_](\d{2,3})[\s\-_\.]',  # 空格01空格 或 -01-
    ]
    
    # 视频文件扩展名
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.rmvb'}
    
    # 字幕文件扩展名
    SUBTITLE_EXTENSIONS = {'.srt', '.ass', '.ssa', '.sub', '.idx', '.vtt'}
    
    # 音频文件扩展名
    AUDIO_EXTENSIONS = {'.mp3', '.flac', '.wav', '.aac', '.m4a', '.ogg', '.wma'}
    
    def parse(self, file_name: str) -> Dict:
        """
        解析文件名
        
        返回:
        {
            "clean_name": "清洗后的名称",
            "file_type": "video/subtitle/audio/image/other",
            "season_number": 季号或None,
            "episode_number": 集号或None,
            "resolution": "4K/1080P/720P或None",
            "video_codec": "HEVC/AVC或None",
            "audio_codec": "DTS/AAC或None"
        }
        """
        result = {
            "clean_name": file_name,
            "file_type": self._detect_file_type(file_name),
            "season_number": None,
            "episode_number": None,
            "resolution": None,
            "video_codec": None,
            "audio_codec": None
        }
        
        # 提取剧集信息
        season, episode = self._extract_episode_info(file_name)
        result["season_number"] = season
        result["episode_number"] = episode
        
        # 提取质量信息
        result["resolution"] = self._extract_resolution(file_name)
        result["video_codec"] = self._extract_video_codec(file_name)
        result["audio_codec"] = self._extract_audio_codec(file_name)
        
        # 清洗文件名
        result["clean_name"] = self._clean_file_name(file_name)
        
        return result
    
    def _detect_file_type(self, file_name: str) -> str:
        """检测文件类型"""
        ext = '.' + file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
        
        if ext in self.VIDEO_EXTENSIONS:
            return "video"
        if ext in self.SUBTITLE_EXTENSIONS:
            return "subtitle"
        if ext in self.AUDIO_EXTENSIONS:
            return "audio"
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
            return "image"
        return "other"
    
    def _extract_episode_info(self, file_name: str) -> Tuple[Optional[int], Optional[int]]:
        """提取季号和集号"""
        for pattern in self.EPISODE_PATTERNS:
            match = re.search(pattern, file_name, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return int(groups[0]), int(groups[1])
                elif len(groups) == 1:
                    return None, int(groups[0])
        return None, None
    
    def _extract_resolution(self, file_name: str) -> Optional[str]:
        """提取分辨率"""
        if re.search(r'4[kK]|2160[pP]', file_name):
            return "4K"
        if re.search(r'1080[pP]', file_name, re.IGNORECASE):
            return "1080P"
        if re.search(r'720[pP]', file_name, re.IGNORECASE):
            return "720P"
        return None
    
    def _extract_video_codec(self, file_name: str) -> Optional[str]:
        """提取视频编码"""
        if re.search(r'HEVC|H\.?265|x265', file_name, re.IGNORECASE):
            return "HEVC"
        if re.search(r'AVC|H\.?264|x264', file_name, re.IGNORECASE):
            return "AVC"
        if re.search(r'AV1', file_name, re.IGNORECASE):
            return "AV1"
        return None
    
    def _extract_audio_codec(self, file_name: str) -> Optional[str]:
        """提取音频编码"""
        if re.search(r'DTS', file_name, re.IGNORECASE):
            return "DTS"
        if re.search(r'AAC', file_name, re.IGNORECASE):
            return "AAC"
        if re.search(r'FLAC', file_name, re.IGNORECASE):
            return "FLAC"
        if re.search(r'TrueHD|Atmos', file_name, re.IGNORECASE):
            return "TrueHD"
        return None
    
    def _clean_file_name(self, file_name: str) -> str:
        """清洗文件名（移除技术信息，保留核心名称）"""
        # 移除扩展名
        name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
        
        # 移除压制组标签
        name = re.sub(r'\[[\w\s&@\-\.]+\]', '', name)
        name = re.sub(r'【[\w\s&@\-\.]+】', '', name)
        
        # 移除技术信息
        name = re.sub(r'(?:Ma)?10p[_\-]?\d{3,4}p?', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\d{3,4}[pP]', '', name)
        name = re.sub(r'4[kK]', '', name)
        
        return name.strip()


# 单例
title_cleaner = TitleCleaner()
file_name_cleaner = FileNameCleaner()

