<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { ref, onMounted, computed, watch } from 'vue'
import { useChatStore } from './stores/chat'
import MarkdownRenderer from './components/MarkdownRenderer.vue'

const chatStore = useChatStore()
const newMessage = ref('')
const chatContainer = ref(null)
const isLoading = ref(false)

// Track if we're in the first message of a new chat
const isNewChat = computed(() => {
    if (!chatStore.activeChat) return true
    return chatStore.activeMessages.length === 0
})

// Check if current chat is empty (has no messages)
const isCurrentChatEmpty = computed(() => {
    return chatStore.activeChat && chatStore.activeMessages.length === 0
})

const sendMessage = async () => {
    if (newMessage.value.trim() === '') return

    const userMessage = newMessage.value
    newMessage.value = ''

    // Store if this is the first message in a new chat before adding message
    const isFirstMessage = isNewChat.value
    const currentChatId = chatStore.activeChatId

    chatStore.addMessage({
        content: userMessage,
        role: 'user',
        timestamp: new Date(),
    })

    isLoading.value = true

    // Add a placeholder message for the AI response that will be updated
    const placeholderId = chatStore.addMessage({
        content: '',
        role: 'assistant',
        timestamp: new Date(),
        isStreaming: true,
    })

    try {
        // Include conversation history for context
        let payload = { message: userMessage }

        if (chatStore.activeMessages.length > 2) {
            // > 2 because we just added user message and placeholder
            payload.history = chatStore.activeMessages
                .slice(0, -2) // exclude the messages we just added
                .map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                }))
        }

        // Set up event source for streaming
        const eventSource = new EventSource(
            `/api/chat?${new URLSearchParams({
                data: JSON.stringify(payload),
            }).toString()}`,
        )

        // Create new AbortController to handle timeouts/errors
        const controller = new AbortController()
        const signal = controller.signal

        // Send the actual request
        const response = await fetch('http://127.0.0.1:5000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
            signal,
        })

        if (!response.ok) {
            throw new Error(`API responded with status: ${response.status}`)
        }

        // Process the stream
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let fullResponse = ''

        // Read the stream
        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            // Decode the chunk and look for JSON data
            const chunk = decoder.decode(value)
            const lines = chunk.split('\n\n')

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6)) // remove 'data: ' prefix

                        if (data.error) {
                            throw new Error(data.error)
                        }

                        if (data.chunk) {
                            fullResponse += data.chunk
                            // Update the message with new content
                            chatStore.updateMessage(placeholderId, fullResponse)
                        }

                        if (data.done) {
                            // Mark the message as complete
                            chatStore.updateMessageStreamingStatus(placeholderId, false)
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data', e)
                    }
                }
            }
        }

        // Generate a meaningful title for new chats after first exchange
        if (isFirstMessage) {
            generateChatTitle(userMessage, currentChatId)
        }
    } catch (error) {
        console.error('Error sending message:', error)
        chatStore.updateMessage(
            placeholderId,
            'Sorry, there was an error processing your request: ' + error.message,
        )
        chatStore.updateMessageStreamingStatus(placeholderId, false)
    } finally {
        isLoading.value = false
        scrollToBottom()
    }
}

const createNewChat = () => {
    // Only create a new chat if the current chat has messages
    // This prevents creating multiple empty chats
    if (!isCurrentChatEmpty.value) {
        chatStore.createNewChat()
    }
}

const scrollToBottom = () => {
    setTimeout(() => {
        if (chatContainer.value) {
            chatContainer.value.scrollTop = chatContainer.value.scrollHeight
        }
    }, 100)
}

const generateChatTitle = async (query, chatId) => {
    try {
        const response = await fetch('/api/chat/title', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query }),
        })

        if (!response.ok) {
            throw new Error(`Title API responded with status: ${response.status}`)
        }

        const data = await response.json()

        if (data.title) {
            // Use the chat ID that was active when the request started
            chatStore.updateChatTitle(chatId, data.title)
        }
    } catch (error) {
        console.error('Error generating chat title:', error)
    }
}

const getNewsQuery = (query) => {
    // First create a new chat if necessary
    if (!chatStore.activeChat) {
        chatStore.createNewChat()
    }

    // Then send the query through the regular chat interface
    newMessage.value = query
    sendMessage()
}

onMounted(() => {
    scrollToBottom()
})

// Watch for changes in active chat to scroll to bottom
watch(
    () => chatStore.activeMessages,
    () => {
        scrollToBottom()
    },
    { deep: true },
)
</script>

<template>
    <!-- Use router-view when on admin route, main chat interface otherwise -->
    <RouterView v-if="$route.path === '/admin'" />

    <main v-else class="relative flex min-h-screen overflow-hidden">
        <aside
            class="custom-scrollbar relative h-screen overflow-x-clip overflow-y-auto rounded-l-3xl border-r border-gray-200 bg-gray-50 transition-all duration-400 ease-in-out min-w-64 w-64"
        >
            <ul class="flex min-w-64 flex-col gap-3 p-2">
                <!-- Admin link -->
                <RouterLink to="/admin">
                    <div
                        class="group relative w-full cursor-pointer rounded-lg p-2 hover:bg-gray-100"
                    >
                        <div class="flex items-center gap-2">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                                class="w-5 h-5"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.281Z"
                                />
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                                />
                            </svg>
                            <span class="text-sm">Feed Management</span>
                        </div>
                    </div>
                </RouterLink>

                <button
                    class="flex items-center gap-2 rounded-lg p-2 hover:bg-gray-100"
                    @click="createNewChat"
                    :disabled="isCurrentChatEmpty"
                    :class="{ 'opacity-50 cursor-not-allowed': isCurrentChatEmpty }"
                >
                    <div class="rounded-full bg-sky-500 p-1 text-white">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="size-4"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M12 4.5v15m7.5-7.5h-15"
                            />
                        </svg>
                    </div>
                    <span class="text-sm font-medium">New Chat</span>
                </button>

                <div class="divider px-2 text-xs text-gray-400">Your Conversations</div>

                <li v-for="chat in chatStore.chats" :key="chat.id">
                    <span class="shrink-0 px-2 text-xs text-gray-500">
                        {{ new Date(chat.createdAt).toLocaleDateString() }}
                    </span>
                    <a
                        class="list-item"
                        @click="chatStore.setActiveChat(chat.id)"
                        :class="{ 'bg-sky-100 rounded-lg': chat.id === chatStore.activeChatId }"
                    >
                        <div class="group relative w-full cursor-pointer rounded-lg p-2">
                            <span
                                class="mask-linear-gradient block overflow-hidden whitespace-nowrap"
                            >
                                {{ chat.title || 'New Chat' }}
                            </span>
                        </div>
                    </a>
                </li>
            </ul>
        </aside>

        <div class="flex flex-1 flex-col h-screen">
            <!-- Main chat area -->
            <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
                <!-- Empty state for new chat -->
                <div
                    v-if="chatStore.activeMessages.length === 0"
                    class="h-full flex flex-col items-center justify-center text-center p-6"
                >
                    <div class="text-4xl mb-6">📰</div>
                    <h2 class="text-xl font-semibold mb-2">News AI Assistant</h2>
                    <p class="text-gray-600 mb-4">
                        Get the latest news updates, summaries and analysis
                    </p>
                    <div class="grid grid-cols-2 gap-3 max-w-lg mx-auto">
                        <button
                            v-for="topic in [
                                'technology',
                                'politics',
                                'health',
                                'business',
                                'sports',
                            ]"
                            :key="topic"
                            @click="getNewsQuery(`Tell me about the latest ${topic} news`)"
                            class="p-2 border rounded-md text-center capitalize hover:bg-gray-50"
                        >
                            Latest {{ topic }}
                        </button>
                    </div>
                </div>

                <!-- Chat messages -->
                <div
                    v-for="(message, idx) in chatStore.activeMessages"
                    :key="idx"
                    :class="[
                        'max-w-3xl mx-auto p-4 rounded-lg',
                        message.role === 'user' ? 'bg-sky-50 ml-auto' : 'bg-gray-50',
                    ]"
                >
                    <div class="text-sm font-semibold mb-1 flex items-center">
                        <span>{{ message.role === 'user' ? 'You' : 'News AI' }}</span>
                        <!-- Streaming indicator -->
                        <div v-if="message.isStreaming" class="ml-2 flex items-center">
                            <div class="w-1.5 h-1.5 bg-sky-500 rounded-full animate-pulse"></div>
                            <div
                                class="w-1.5 h-1.5 bg-sky-500 rounded-full animate-pulse ml-1"
                                style="animation-delay: 0.2s"
                            ></div>
                            <div
                                class="w-1.5 h-1.5 bg-sky-500 rounded-full animate-pulse ml-1"
                                style="animation-delay: 0.4s"
                            ></div>
                        </div>
                    </div>

                    <!-- User messages displayed as plain text -->
                    <div v-if="message.role === 'user'">{{ message.content }}</div>

                    <!-- AI messages rendered with markdown -->
                    <MarkdownRenderer v-else :content="message.content" />

                    <!-- Time display -->
                    <div class="text-xs text-gray-400 mt-2">
                        {{ new Date(message.timestamp).toLocaleTimeString() }}
                    </div>
                </div>

                <!-- Loading indicator -->
                <div
                    v-if="isLoading && chatStore.activeMessages.length === 0"
                    class="max-w-3xl mx-auto p-4 rounded-lg bg-gray-50"
                >
                    <div class="text-sm font-semibold mb-1">News AI</div>
                    <div class="flex items-center gap-2">
                        <div class="animate-pulse">Searching news sources</div>
                        <div class="flex items-center gap-1">
                            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div
                                class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                style="animation-delay: 0.2s"
                            ></div>
                            <div
                                class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                style="animation-delay: 0.4s"
                            ></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Input form -->
            <div class="border-t border-gray-200 p-4">
                <form @submit.prevent="sendMessage" class="flex items-center gap-2">
                    <input
                        v-model="newMessage"
                        type="text"
                        placeholder="Ask about news, events, or topics..."
                        class="flex-1 rounded-lg border border-gray-300 p-3 focus:border-sky-500 focus:outline-none"
                        :disabled="isLoading"
                    />
                    <button
                        type="submit"
                        class="rounded-lg bg-sky-500 p-3 text-white hover:bg-sky-600 disabled:opacity-50"
                        :disabled="isLoading || newMessage.trim() === ''"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="size-5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                            />
                        </svg>
                    </button>
                </form>
            </div>
        </div>
    </main>
</template>

<style>
.mask-linear-gradient {
    mask-image: linear-gradient(to left, transparent, black 20px);
}

.custom-scrollbar::-webkit-scrollbar {
    width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(156, 163, 175, 0.5);
    border-radius: 20px;
}

.divider {
    display: flex;
    align-items: center;
    margin: 0.5rem 0;
}

.divider::before,
.divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid rgba(156, 163, 175, 0.2);
}

.divider::before {
    margin-right: 0.5rem;
}

.divider::after {
    margin-left: 0.5rem;
}
</style>
