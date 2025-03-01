document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const chatMessages = document.getElementById('chat-messages');
    const questionInput = document.getElementById('question-input');
    const sendBtn = document.getElementById('send-btn');
    const toggleSummary = document.getElementById('toggle-summary');
    const summaryContent = document.getElementById('summary-content');
    const downloadPdf = document.getElementById('download-pdf');

    let summary = '';

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();
        const files = document.getElementById('pdf-files').files;
        
        for (let file of files) {
            formData.append('files[]', file);
        }

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }

            summary = data.summary;
            alert('PDFs processed successfully!');
        } catch (error) {
            alert('Error processing PDFs');
        }
    });

    async function sendMessage() {
        const question = questionInput.value.trim();
        if (!question) return;

        // Add user message
        addMessage(question, 'user');
        questionInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }

            // Add bot message with sources
            const sourceText = data.sources.length > 0 
                ? `\n\nSources: ${data.sources.join(', ')}` 
                : '';
            addMessage(data.answer + sourceText, 'bot');
        } catch (error) {
            alert('Error sending message');
        }
    }

    function addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.textContent = content;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    toggleSummary.addEventListener('click', () => {
        if (summaryContent.classList.contains('hidden')) {
            summaryContent.textContent = summary;
            summaryContent.classList.remove('hidden');
            toggleSummary.textContent = 'Hide Summary';
        } else {
            summaryContent.classList.add('hidden');
            toggleSummary.textContent = 'Show Summary';
        }
    });

    downloadPdf.addEventListener('click', async () => {
        try {
            const response = await fetch('/download-pdf', {
                method: 'POST'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'conversation.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } else {
                alert('Error downloading PDF');
            }
        } catch (error) {
            alert('Error downloading PDF');
        }
    });
}); 