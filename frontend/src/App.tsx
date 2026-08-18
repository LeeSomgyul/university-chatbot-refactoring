import { useState } from 'react';
import Header from './layout/header';
import ChatInterface from './layout/ChatInterface';
import Notice from './layout/notice';
import Guide from './layout/Guide';
import './App.css';
import './index.css';

interface Message {
    sender: string;
    text: string | React.ReactNode;
    time: string;
}

const App = () => {
    // 채팅 메시지 상태 관리
    const [messages, setMessages] = useState<Message[]>([]);

    // 채팅 초기화 함수
    const resetChat = () => {
        setMessages([]);
    };

    return (
        <div>
            <Header onResetChat={resetChat} />

            <Notice />
            <div className='main-container'>
                <ChatInterface messages={messages} setMessages={setMessages} />  
                <Guide />
            </div>
        </div>
    );
};

export default App;