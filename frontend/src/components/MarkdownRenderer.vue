<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import { sanitize } from '../utils/sanitize'

const props = defineProps({
    content: {
        type: String,
        required: true,
        default: '',
    },
    options: {
        type: Object,
        default: () => ({}),
    },
})

const renderedContent = computed(() => {
    if (!props.content) return ''

    // Configure marked options
    const defaultOptions = {
        breaks: true, // Convert line breaks to <br>
        gfm: true, // GitHub Flavored Markdown
        headerIds: false, // Disable header IDs for security
    }

    marked.setOptions({
        ...defaultOptions,
        ...props.options,
    })

    // Parse and sanitize content
    const parsed = marked.parse(props.content)
    return sanitize(parsed)
})
</script>

<template>
    <div class="markdown-content" v-html="renderedContent"></div>
</template>

<style scoped>
.markdown-content :deep(p) {
    margin-bottom: 0.75rem;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
    font-weight: 600;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}

.markdown-content :deep(h1) {
    font-size: 1.5rem;
}
.markdown-content :deep(h2) {
    font-size: 1.25rem;
}
.markdown-content :deep(h3) {
    font-size: 1.125rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
    padding-left: 1.5rem;
    margin-bottom: 1rem;
}

.markdown-content :deep(ul) {
    list-style-type: disc;
}
.markdown-content :deep(ol) {
    list-style-type: decimal;
}

.markdown-content :deep(li) {
    margin-bottom: 0.25rem;
}

.markdown-content :deep(a) {
    color: #0ea5e9; /* sky-500 */
    text-decoration: underline;
}

.markdown-content :deep(blockquote) {
    border-left: 3px solid #e5e7eb; /* gray-200 */
    padding-left: 1rem;
    color: #6b7280; /* gray-500 */
    font-style: italic;
    margin: 1rem 0;
}

.markdown-content :deep(code) {
    font-family: monospace;
    background-color: #f3f4f6; /* gray-100 */
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
}

.markdown-content :deep(pre) {
    background-color: #f3f4f6; /* gray-100 */
    padding: 1rem;
    border-radius: 0.25rem;
    overflow-x: auto;
    margin: 1rem 0;
}

.markdown-content :deep(pre code) {
    background-color: transparent;
    padding: 0;
}

.markdown-content :deep(hr) {
    border: 0;
    border-top: 1px solid #e5e7eb; /* gray-200 */
    margin: 1rem 0;
}

.markdown-content :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
    padding: 0.5rem;
    border: 1px solid #e5e7eb; /* gray-200 */
}

.markdown-content :deep(th) {
    background-color: #f3f4f6; /* gray-100 */
    font-weight: 600;
}

.markdown-content :deep(tr:nth-child(even)) {
    background-color: #f9fafb; /* gray-50 */
}
</style>
