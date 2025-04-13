/**
 * Basic HTML sanitizer to prevent XSS attacks
 * Note: In a production environment, consider using a more robust solution like DOMPurify
 *
 * @param {string} html - Raw HTML content to sanitize
 * @returns {string} - Sanitized HTML
 */
export function sanitize(html) {
    if (!html) return ''

    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = html

    // Remove potentially dangerous elements
    const dangerousElements = tempDiv.querySelectorAll('script, iframe, object, embed, form')
    dangerousElements.forEach((el) => el.remove())

    // Remove dangerous attributes from all elements
    const allElements = tempDiv.getElementsByTagName('*')
    for (const element of allElements) {
        // Remove event handler attributes
        for (const attribute of [...element.attributes]) {
            const name = attribute.name.toLowerCase()

            if (
                name.startsWith('on') || // event handlers
                (name === 'href' && attribute.value.toLowerCase().startsWith('javascript:')) ||
                (name === 'src' && attribute.value.toLowerCase().startsWith('javascript:')) ||
                (name === 'data' && attribute.value.toLowerCase().startsWith('javascript:'))
            ) {
                element.removeAttribute(name)
            }
        }
    }

    return tempDiv.innerHTML
}
