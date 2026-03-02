document.addEventListener('DOMContentLoaded', () => {
    let activeTextarea = null;
    let autocompleteContainer = null;
    
    // Create the global autocomplete dropdown container
    autocompleteContainer = document.createElement('div');
    autocompleteContainer.className = 'editor-autocomplete-dropdown glassmorphism';
    document.body.appendChild(autocompleteContainer);
    
    function hideAutocomplete() {
        autocompleteContainer.style.display = 'none';
        autocompleteContainer.innerHTML = '';
        activeTextarea = null;
    }

    document.addEventListener('input', async (e) => {
        if (e.target.tagName === 'TEXTAREA') {
            const textarea = e.target;
            const text = textarea.value;
            const cursorPos = textarea.selectionStart;
            
            // Look backwards from cursor for '[' or '@'
            const textBeforeCursor = text.substring(0, cursorPos);
            const match = textBeforeCursor.match(/([\[@])([^\[@\n]{0,30})$/);
            
            if (match) {
                const triggerChar = match[1];
                const query = match[2];
                activeTextarea = textarea;

                const rect = textarea.getBoundingClientRect();
                autocompleteContainer.style.display = 'block';
                autocompleteContainer.style.top = `${rect.bottom + window.scrollY + 5}px`;
                autocompleteContainer.style.left = `${rect.left + window.scrollX}px`;
                autocompleteContainer.style.width = `${Math.max(300, rect.width * 0.5)}px`;
                
                if (query.length > 0) {
                    autocompleteContainer.innerHTML = '<div class="autocomplete-loading">Searching...</div>';
                    try {
                        const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
                        const results = await res.json();
                        
                        if (results.length === 0) {
                            autocompleteContainer.innerHTML = '<div class="autocomplete-empty">No matches found</div>';
                            return;
                        }
                        
                        autocompleteContainer.innerHTML = '';
                        results.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'autocomplete-item';
                            div.innerHTML = `<strong>${item.title}</strong> <small>(${item.type})</small>`;
                            div.onmousedown = (e) => {
                                e.preventDefault(); // keep focus
                                insertLink(textarea, triggerChar, match[0].length, item);
                            };
                            autocompleteContainer.appendChild(div);
                        });
                    } catch (err) {
                        autocompleteContainer.innerHTML = '<div class="autocomplete-error">Error fetching data</div>';
                    }
                } else {
                    autocompleteContainer.innerHTML = '<div class="autocomplete-hint">Type to search...</div>';
                }
            } else {
                hideAutocomplete();
            }
        }
    });

    document.addEventListener('mousedown', (e) => {
        if (autocompleteContainer.style.display === 'block' && !autocompleteContainer.contains(e.target)) {
            hideAutocomplete();
        }
    });
    
    function insertLink(textarea, triggerChar, matchLength, item) {
        const text = textarea.value;
        const cursorPos = textarea.selectionStart;
        const before = text.substring(0, cursorPos - matchLength);
        const after = text.substring(cursorPos);
        
        // Make standard markdown link
        const link = `[${item.title}](/${item.type}/${item.id}/)`; 
        
        textarea.value = before + link + after;
        textarea.selectionStart = textarea.selectionEnd = before.length + link.length;
        textarea.focus();
        
        hideAutocomplete();
        
        // Trigger generic input event so HTMX/frameworks know it changed
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }
});
