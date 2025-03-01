css = '''
<style>
    /* Chat message container */
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        transition: all 0.3s ease;
    }
    
    /* User message styling */
    .chat-message.user {
        background-color: #2b313e;
        justify-content: flex-end;
    }
    
    /* Bot message styling */
    .chat-message.bot {
        background-color: #475063;
        justify-content: flex-start;
    }

    /* Avatar styling */
    .chat-message .avatar {
        width: 20%;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .chat-message .avatar img {
        max-width: 78px;
        max-height: 78px;
        border-radius: 50%;
        object-fit: cover;
        transition: transform 0.3s ease;
    }

    /* Message content styling */
    .chat-message .message {
        width: 80%;
        padding: 0 1.5rem;
        color: #fff;
    }

    /* Hover effect on avatar */
    .chat-message .avatar img:hover {
        transform: scale(1.1);
    }

    /* Chat container hover effect */
    .chat-message:hover {
        background-color: #3c4452;
    }
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://i.ibb.co/cN0nmSj/Screenshot-2023-05-28-at-02-37-21.png" alt="Bot Avatar">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://i.ibb.co/rdZC7LZ/Photo-logo-1.png" alt="User Avatar">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''
