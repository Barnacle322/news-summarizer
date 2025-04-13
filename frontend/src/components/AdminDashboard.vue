<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const activeTask = ref(null)
const taskStatus = ref(null)
const isLoading = ref(false)
const error = ref(null)
const pollingInterval = ref(null)
const schedulerStatus = ref(null)

// Start a new feed fetch task
const startFeedFetch = async () => {
    try {
        isLoading.value = true
        error.value = null

        const response = await fetch('http://127.0.0.1:5000/api/feeds/fetch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })

        if (!response.ok) {
            throw new Error(`API responded with status: ${response.status}`)
        }

        const data = await response.json()
        activeTask.value = data.task_id

        // Start polling for status updates
        startStatusPolling()
    } catch (err) {
        error.value = `Error starting feed fetch: ${err.message}`
    } finally {
        isLoading.value = false
    }
}

// Poll for status updates on the active task
const startStatusPolling = () => {
    // Clear any existing polling interval
    stopStatusPolling()

    // Start polling every 2 seconds
    pollingInterval.value = setInterval(async () => {
        if (!activeTask.value) {
            stopStatusPolling()
            return
        }

        try {
            const response = await fetch(
                `http://127.0.0.1:5000/api/feeds/tasks/${activeTask.value}`,
            )

            if (!response.ok) {
                if (response.status === 404) {
                    // Task not found, stop polling
                    stopStatusPolling()
                    error.value = 'Task not found or expired'
                    return
                }
                throw new Error(`API responded with status: ${response.status}`)
            }

            const data = await response.json()
            taskStatus.value = data.task

            // If the task is completed or failed, stop polling
            if (['completed', 'failed'].includes(taskStatus.value.status)) {
                stopStatusPolling()
            }
        } catch (err) {
            error.value = `Error checking task status: ${err.message}`
        }
    }, 1000) // Poll more frequently (every second) to make progress bar smoother
}

// Stop polling for status updates
const stopStatusPolling = () => {
    if (pollingInterval.value) {
        clearInterval(pollingInterval.value)
        pollingInterval.value = null
    }
}

// Get the overall scheduler status
const getSchedulerStatus = async () => {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/feeds/status')

        if (!response.ok) {
            throw new Error(`API responded with status: ${response.status}`)
        }

        const data = await response.json()
        schedulerStatus.value = data
    } catch (err) {
        console.error('Error getting scheduler status:', err)
    }
}

// Format duration as minutes and seconds
const formatDuration = (seconds) => {
    if (!seconds) return ''
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
}

onMounted(() => {
    // Get initial scheduler status
    getSchedulerStatus()

    // Check if there's a task in progress from a previous session
    const savedTaskId = localStorage.getItem('active_feed_task')
    if (savedTaskId) {
        activeTask.value = savedTaskId
        startStatusPolling()
    }
})

onBeforeUnmount(() => {
    // Clean up polling interval
    stopStatusPolling()
})

// Watch for changes in active task and save to localStorage
watch(activeTask, (newTaskId) => {
    if (newTaskId) {
        localStorage.setItem('active_feed_task', newTaskId)
    } else {
        localStorage.removeItem('active_feed_task')
    }
})

// Clear task when completed
watch(
    () => taskStatus.value?.status,
    (newStatus) => {
        if (newStatus === 'completed' || newStatus === 'failed') {
            // Keep the task ID for a bit so the user can see the results,
            // but remove from localStorage so it doesn't reload on refresh
            localStorage.removeItem('active_feed_task')
        }
    },
)
</script>

<template>
    <div class="admin-dashboard bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4">News Feed Management</h2>

        <div class="mb-6">
            <h3 class="text-lg font-medium mb-2">Scheduler Status</h3>
            <div v-if="schedulerStatus" class="bg-gray-50 p-3 rounded border">
                <div class="mb-2">
                    <span class="font-semibold">Status:</span>
                    <span
                        :class="{
                            'text-green-600': schedulerStatus.status === 'running',
                            'text-red-600': schedulerStatus.status !== 'running',
                        }"
                    >
                        {{ schedulerStatus.status }}
                    </span>
                </div>
                <div v-if="schedulerStatus.jobs && schedulerStatus.jobs.length">
                    <p class="text-sm font-semibold mb-1">Scheduled Jobs:</p>
                    <ul class="text-sm">
                        <li v-for="job in schedulerStatus.jobs" :key="job.id" class="mb-1">
                            {{ job.name }} - Next run: {{ new Date(job.next_run).toLocaleString() }}
                        </li>
                    </ul>
                </div>
            </div>
            <div v-else class="text-gray-500">Loading scheduler status...</div>
        </div>

        <div class="mb-6">
            <h3 class="text-lg font-medium mb-3">Manual Feed Fetch</h3>
            <button
                @click="startFeedFetch"
                class="bg-sky-500 text-white px-4 py-2 rounded hover:bg-sky-600 disabled:opacity-50"
                :disabled="
                    isLoading ||
                    (activeTask &&
                        taskStatus &&
                        ['starting', 'running'].includes(taskStatus.status))
                "
            >
                <span v-if="isLoading">Starting...</span>
                <span
                    v-else-if="
                        activeTask &&
                        taskStatus &&
                        ['starting', 'running'].includes(taskStatus.status)
                    "
                >
                    Feed fetch in progress...
                </span>
                <span v-else>Start Feed Fetch</span>
            </button>
        </div>

        <div v-if="error" class="bg-red-100 border border-red-300 text-red-800 p-3 rounded mb-4">
            {{ error }}
        </div>

        <div v-if="taskStatus" class="bg-gray-50 border rounded p-4">
            <h4 class="font-medium mb-2">Current Task Status</h4>

            <div class="mb-3">
                <div class="flex items-center mb-1">
                    <span class="font-semibold mr-2">Status:</span>
                    <span
                        :class="{
                            'text-yellow-600':
                                taskStatus.status === 'running' || taskStatus.status === 'starting',
                            'text-green-600': taskStatus.status === 'completed',
                            'text-red-600': taskStatus.status === 'failed',
                        }"
                    >
                        {{ taskStatus.status.charAt(0).toUpperCase() + taskStatus.status.slice(1) }}
                    </span>
                </div>

                <div class="mb-2 text-sm">
                    <span v-if="taskStatus.status_message">{{ taskStatus.status_message }}</span>
                </div>

                <div v-if="taskStatus.progress !== undefined" class="mb-2">
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                            class="bg-sky-500 h-2.5 rounded-full transition-all duration-200"
                            :style="`width: ${taskStatus.progress}%`"
                            :class="{ 'animate-pulse': taskStatus.status === 'running' }"
                        ></div>
                    </div>
                    <span class="text-xs text-gray-600">{{ taskStatus.progress }}%</span>
                </div>

                <div class="text-sm grid grid-cols-2 gap-2">
                    <div>
                        <span class="font-semibold">Started:</span>
                        {{
                            taskStatus.started_at_formatted
                                ? new Date(taskStatus.started_at_formatted).toLocaleString()
                                : 'N/A'
                        }}
                    </div>
                    <div>
                        <span class="font-semibold">Completed:</span>
                        {{
                            taskStatus.completed_at_formatted
                                ? new Date(taskStatus.completed_at_formatted).toLocaleString()
                                : 'In progress...'
                        }}
                    </div>
                    <div v-if="taskStatus.duration_seconds">
                        <span class="font-semibold">Duration:</span>
                        {{ formatDuration(taskStatus.duration_seconds) }}
                    </div>
                </div>
            </div>

            <!-- Additional statistics when available -->
            <div v-if="taskStatus.stats" class="mt-3 pt-3 border-t text-sm">
                <h5 class="font-medium mb-2">Processing Statistics:</h5>
                <div class="grid grid-cols-3 gap-2">
                    <div>
                        <div class="font-semibold">Feeds:</div>
                        <div>{{ taskStatus.stats.processed_feeds || 0 }}</div>
                    </div>
                    <div>
                        <div class="font-semibold">Articles Found:</div>
                        <div>{{ taskStatus.stats.total_found || 0 }}</div>
                    </div>
                    <div>
                        <div class="font-semibold">Articles Processed:</div>
                        <div>{{ taskStatus.stats.processed_articles || 0 }}</div>
                    </div>
                </div>
            </div>

            <div
                v-if="taskStatus.result && Object.keys(taskStatus.result).length"
                class="mt-3 pt-3 border-t"
            >
                <h5 class="font-medium mb-2">Results:</h5>
                <div class="grid grid-cols-3 gap-2 text-center">
                    <div class="bg-green-100 p-2 rounded">
                        <div class="text-lg font-bold text-green-700">
                            {{ taskStatus.result.new || 0 }}
                        </div>
                        <div class="text-xs text-green-800">New Articles</div>
                    </div>
                    <div class="bg-yellow-100 p-2 rounded">
                        <div class="text-lg font-bold text-yellow-700">
                            {{ taskStatus.result.duplicates || 0 }}
                        </div>
                        <div class="text-xs text-yellow-800">Duplicates</div>
                    </div>
                    <div class="bg-red-100 p-2 rounded">
                        <div class="text-lg font-bold text-red-700">
                            {{ taskStatus.result.errors || 0 }}
                        </div>
                        <div class="text-xs text-red-800">Errors</div>
                    </div>
                </div>
            </div>

            <div v-if="taskStatus.error" class="mt-3 text-red-600">
                <span class="font-semibold">Error:</span> {{ taskStatus.error }}
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Add any component-specific styles here */
.animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%,
    100% {
        opacity: 1;
    }
    50% {
        opacity: 0.7;
    }
}
</style>
