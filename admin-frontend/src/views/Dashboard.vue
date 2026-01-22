<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #409EFF;">
              <el-icon :size="28"><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_users }}</div>
              <div class="stat-label">总用户数</div>
              <div class="stat-trend up">今日 +{{ stats.today_users }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #67C23A;">
              <el-icon :size="28"><Share /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_shares }}</div>
              <div class="stat-label">总分享数</div>
              <div class="stat-trend up">今日 +{{ stats.today_shares }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #E6A23C;">
              <el-icon :size="28"><View /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatNumber(stats.total_views) }}</div>
              <div class="stat-label">总浏览量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #F56C6C;">
              <el-icon :size="28"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pending_shares }}</div>
              <div class="stat-label">待审核</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>数据趋势</span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrends">
                <el-radio-button :value="7">7天</el-radio-button>
                <el-radio-button :value="14">14天</el-radio-button>
                <el-radio-button :value="30">30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="trendChartOption" style="height: 300px;" autoresize />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>网盘类型分布</span></template>
          <v-chart :option="driveTypeChartOption" style="height: 300px;" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 排行榜 -->
    <el-row :gutter="20" class="rank-row">
      <el-col :span="8">
        <el-card>
          <template #header><span>🔥 热门分享</span></template>
          <div class="rank-list">
            <div v-for="(item, index) in rankings.hot_shares" :key="item.id" class="rank-item">
              <span class="rank-num" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="rank-title">{{ item.title }}</span>
              <span class="rank-count">{{ item.count }} 次</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>💾 转存排行</span></template>
          <div class="rank-list">
            <div v-for="(item, index) in rankings.top_saves" :key="item.id" class="rank-item">
              <span class="rank-num" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="rank-title">{{ item.title }}</span>
              <span class="rank-count">{{ item.count }} 次</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>👑 活跃分享者</span></template>
          <div class="rank-list">
            <div v-for="(item, index) in rankings.top_sharers" :key="item.id" class="rank-item">
              <span class="rank-num" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="rank-title">{{ item.nickname || item.username }}</span>
              <span class="rank-count">{{ item.share_count }} 个</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { statsApi, type OverviewStats, type TrendStats, type RankStats } from '@/api'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const stats = reactive<OverviewStats>({
  total_users: 0, total_shares: 0, total_views: 0, total_saves: 0,
  today_users: 0, today_shares: 0, active_users: 0, pending_shares: 0
})

const trends = ref<TrendStats>({ users: [], shares: [], views: [] })
const rankings = ref<RankStats>({ hot_shares: [], top_saves: [], top_sharers: [] })
const driveTypes = ref<Array<{ drive_type: string; count: number; percentage: number }>>([])
const trendDays = ref(7)

const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['新增用户', '新增分享'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: trends.value.users.map(i => i.date.slice(5)) },
  yAxis: { type: 'value' },
  series: [
    { name: '新增用户', type: 'line', smooth: true, data: trends.value.users.map(i => i.count) },
    { name: '新增分享', type: 'line', smooth: true, data: trends.value.shares.map(i => i.count) }
  ]
}))

const driveTypeChartOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: driveTypes.value.map(d => ({ name: getDriveTypeName(d.drive_type), value: d.count }))
  }]
}))

function getDriveTypeName(type: string) {
  const map: Record<string, string> = { tianyi: '天翼云盘', aliyun: '阿里云盘', quark: '夸克网盘' }
  return map[type] || type
}

function formatNumber(num: number) {
  if (num >= 10000) return (num / 10000).toFixed(1) + 'w'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return num.toString()
}

async function loadStats() {
  try {
    Object.assign(stats, await statsApi.overview())
  } catch (e) { console.error(e) }
}

async function loadTrends() {
  try {
    trends.value = await statsApi.trends(trendDays.value)
  } catch (e) { console.error(e) }
}

async function loadRankings() {
  try {
    rankings.value = await statsApi.rankings(10)
  } catch (e) { console.error(e) }
}

async function loadDriveTypes() {
  try {
    driveTypes.value = await statsApi.driveTypes()
  } catch (e) { console.error(e) }
}

onMounted(() => {
  loadStats()
  loadTrends()
  loadRankings()
  loadDriveTypes()
})
</script>

<style scoped lang="scss">
.dashboard { .stat-cards { margin-bottom: 20px; } }
.stat-card {
  display: flex; align-items: center; gap: 16px;
  .stat-icon {
    width: 60px; height: 60px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; color: #fff;
  }
  .stat-info { flex: 1; }
  .stat-value { font-size: 28px; font-weight: bold; color: #303133; }
  .stat-label { font-size: 14px; color: #909399; margin-top: 4px; }
  .stat-trend { font-size: 12px; margin-top: 4px; &.up { color: #67c23a; } }
}
.chart-row, .rank-row { margin-bottom: 20px; }
.rank-list {
  .rank-item {
    display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0;
    &:last-child { border-bottom: none; }
    .rank-num {
      width: 24px; height: 24px; border-radius: 4px; background: #f0f0f0;
      display: flex; align-items: center; justify-content: center;
      font-size: 12px; font-weight: bold; margin-right: 12px;
      &.top { background: #409EFF; color: #fff; }
    }
    .rank-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
    .rank-count { font-size: 12px; color: #909399; }
  }
}
</style>

