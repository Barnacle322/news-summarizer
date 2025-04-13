import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { v4 as uuidv4 } from 'uuid'

export const useChatStore = defineStore('chat', () => {
    const chats = ref([])
    const activeChatId = ref(null)

    // Create initial chat if none exists
    if (chats.value.length === 0) {
        createNewChat()
    }

    function createNewChat() {
        const newChat = {
            id: uuidv4(),
            title: 'New Chat',
            createdAt: new Date().toISOString(),
            messages: [],
        }

        // Add new chat at the beginning of the array (newest first)
        chats.value.unshift(newChat)
        activeChatId.value = newChat.id
        return newChat
    }

    function setActiveChat(chatId) {
        activeChatId.value = chatId
    }

    function addMessage(message) {
        const chat = chats.value.find((c) => c.id === activeChatId.value)
        const messageId = uuidv4()

        if (chat) {
            chat.messages.push({
                ...message,
                id: messageId,
            })
        }

        return messageId
    }

    function updateMessage(messageId, content) {
        const chat = chats.value.find((c) => c.id === activeChatId.value)
        if (chat) {
            const message = chat.messages.find((m) => m.id === messageId)
            if (message) {
                message.content = content
            }
        }
    }

    function updateMessageStreamingStatus(messageId, isStreaming) {
        const chat = chats.value.find((c) => c.id === activeChatId.value)
        if (chat) {
            const message = chat.messages.find((m) => m.id === messageId)
            if (message) {
                message.isStreaming = isStreaming
            }
        }
    }

    function updateChatTitle(chatId, newTitle) {
        const chat = chats.value.find((c) => c.id === chatId)
        if (chat) {
            chat.title = newTitle
        }
    }

    function deleteChat(chatId) {
        const index = chats.value.findIndex((c) => c.id === chatId)

        if (index !== -1) {
            chats.value.splice(index, 1)

            // If we deleted the active chat, set a new active chat
            if (activeChatId.value === chatId) {
                activeChatId.value = chats.value.length > 0 ? chats.value[0].id : null

                // If we have no more chats, create a new one
                if (activeChatId.value === null) {
                    createNewChat()
                }
            }
        }
    }

    // For persistence to localStorage
    function saveChats() {
        try {
            localStorage.setItem('news-ai-chats', JSON.stringify(chats.value))
            localStorage.setItem('news-ai-active-chat', activeChatId.value)
        } catch (e) {
            console.error('Failed to save chats to localStorage:', e)
        }
    }

    function loadChats() {
        try {
            const savedChats = localStorage.getItem('news-ai-chats')
            const savedActiveChatId = localStorage.getItem('news-ai-active-chat')

            if (savedChats) {
                chats.value = JSON.parse(savedChats)

                // Ensure timestamps are Date objects
                chats.value.forEach((chat) => {
                    chat.messages.forEach((message) => {
                        if (typeof message.timestamp === 'string') {
                            message.timestamp = new Date(message.timestamp)
                        }
                    })
                })

                // Sort chats by creation date (newest first)
                chats.value.sort((a, b) => {
                    return new Date(b.createdAt) - new Date(a.createdAt)
                })
            }

            if (savedActiveChatId) {
                activeChatId.value = savedActiveChatId

                // Validate that the active chat still exists
                if (!chats.value.some((c) => c.id === activeChatId.value)) {
                    activeChatId.value = chats.value.length > 0 ? chats.value[0].id : null
                }
            }

            // If there are no chats, create a new one
            if (chats.value.length === 0) {
                createNewChat()
            }
        } catch (e) {
            console.error('Failed to load chats from localStorage:', e)
            if (chats.value.length === 0) {
                createNewChat()
            }
        }
    }

    // Call loadChats on store initialization
    loadChats()

    // Watch for changes and save to localStorage
    function watchAndSave() {
        let saveTimeout
        return () => {
            clearTimeout(saveTimeout)
            saveTimeout = setTimeout(() => {
                saveChats()
            }, 500) // Debounce saves
        }
    }

    const activeChat = computed(() => {
        return chats.value.find((c) => c.id === activeChatId.value) || null
    })

    const activeMessages = computed(() => {
        return activeChat.value ? activeChat.value.messages : []
    })

    // Sort chats by created date, newest first
    const sortedChats = computed(() => {
        return [...chats.value].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    })

    // Set up watchers for chat changes
    if (typeof window !== 'undefined') {
        const saveDebounced = watchAndSave()

        // Watch for changes in chats and save
        const unwatch = setInterval(() => {
            saveDebounced()
        }, 5000)

        // Clean up interval on module unload
        if (import.meta.hot) {
            import.meta.hot.dispose(() => {
                clearInterval(unwatch)
            })
        }
    }

    return {
        chats: sortedChats, // Return the sorted computed property instead of raw ref
        activeChatId,
        activeChat,
        activeMessages,
        createNewChat,
        setActiveChat,
        addMessage,
        updateMessage,
        updateMessageStreamingStatus,
        updateChatTitle,
        deleteChat,
        saveChats,
        loadChats,
    }
})
