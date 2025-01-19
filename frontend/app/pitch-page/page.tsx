'use client';
import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';

export default function PitchPage() {
  const [time, setTime] = useState(300);
  const [videoWebSocket, setVideoWebSocket] = useState<WebSocket | null>(null);
  const [transcriptWebSocket, setTranscriptWebSocket] = useState<WebSocket | null>(null);

  const [isSessionActive, setIsSessionActive] = useState(false);
  const [transcript, setTranscript] = useState<Array<{ speaker: string; text: string }>>([]);

  const videoRef = useRef<HTMLImageElement>(null);

  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSessionActive && time > 0) {
      interval = setInterval(() => setTime((t) => t - 1), 1000);
    }
    return () => clearInterval(interval);
  }, [isSessionActive, time]);

  // Cleanup websockets on unmount
  useEffect(() => {
    return () => {
      if (videoWebSocket) videoWebSocket.close();
      if (transcriptWebSocket) transcriptWebSocket.close();
    };
  }, [videoWebSocket, transcriptWebSocket]);

  async function handleStart() {
    // 1) Start Chat
    const res = await fetch('http://127.0.0.1:8000/start_chat');
    const data = await res.json();
    console.log('start_chat:', data);

    // 2) WebSocket for video
    const wsVideo = new WebSocket('ws://127.0.0.1:8000/ws');
    wsVideo.onopen = () => console.log("Video WS open");
    wsVideo.onmessage = (evt) => {
      if (videoRef.current) {
        videoRef.current.src = URL.createObjectURL(new Blob([evt.data], { type: 'image/jpeg' }));
      }
    };
    wsVideo.onerror = (err) => console.error("Video WS error:", err);
    wsVideo.onclose = () => console.log("Video WS closed");
    setVideoWebSocket(wsVideo);

    // 3) WebSocket for transcript
    const wsTx = new WebSocket('ws://127.0.0.1:8000/ws_transcript');
    wsTx.onopen = () => console.log("Transcript WS open");
    wsTx.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        setTranscript(prev => [...prev, { speaker: msg.speaker, text: msg.text }]);
      } catch (e) {
        console.error('Transcript parse error:', e);
      }
    };
    wsTx.onerror = (err) => console.error("Transcript WS error:", err);
    wsTx.onclose = () => console.log("Transcript WS closed");
    setTranscriptWebSocket(wsTx);

    setIsSessionActive(true);
    setTime(300);
  }

  async function handleBeginQnA() {
    const res = await fetch('http://127.0.0.1:8000/begin_qna');
    const data = await res.json();
    console.log('begin_qna:', data);
  }

  async function handleStop() {
    // First stop everything as before
    const res = await fetch('http://127.0.0.1:8000/stop');
    const dat = await res.json();
    console.log('stop_all:', dat);
  
    // Generate analysis with current timer value and transcript
    try {
      const analysisRes = await fetch('http://127.0.0.1:8000/generate_analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          time_left: time,
          transcript: transcript  // Send the entire transcript array
        })
      });
      
      const analysisData = await analysisRes.json();
      console.log('Analysis generated:', analysisData);
    } catch (error) {
      console.error('Error generating analysis:', error);
    }
  
    // Continue with cleanup as before
    if (videoWebSocket) videoWebSocket.close();
    if (transcriptWebSocket) transcriptWebSocket.close();
  
    setVideoWebSocket(null);
    setTranscriptWebSocket(null);
    setIsSessionActive(false);
    setTranscript([]);
    setTime(300);
    if (videoRef.current) {
      videoRef.current.src = '';
    }
  }
  
  return (
    <div className="min-h-screen bg-[#14121f]">
      <div className="max-w-[1400px] mx-auto px-8">
         {/* Updated Navbar */}
         <nav className="flex justify-between items-center p-6 max-w-[1400px] mx-auto">
          <Link href="/">
            <Image 
              src="/images/logopitch.png"
              alt="Logo"
              width={180}
              height={40}
              className="hover:opacity-90 transition-opacity"
            />
          </Link>
          <div className="border border-transparent bg-gradient-to-r from-violet-500 via-blue-500 to-indigo-500 rounded-lg p-[1px]">
            <div className="bg-[rgb(40,40,45)] rounded-lg px-6 py-3">
              <a href="/" className="text-white text-xl font-medium hover:opacity-80 transition-opacity">
                Home
              </a>
            </div>
          </div>
        </nav>

        <h1 className="text-6xl font-bold bg-gradient-to-r from-[#6366f1] to-[#4f46e5]
                       bg-clip-text text-transparent mb-8">
          Pitch
        </h1>

        <div className="flex gap-8">
          <div className="flex-1">
            {/* Buttons */}
            <div className="flex items-center gap-4 mb-4">
              <button
                onClick={handleStart}
                disabled={isSessionActive}
                className={`px-6 py-2 rounded-md ${
                  isSessionActive ? 'bg-gray-500 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'
                } text-white`}
              >
                Start
              </button>

              <button
                onClick={handleBeginQnA}
                disabled={!isSessionActive}
                className={`px-6 py-2 rounded-md ${
                  !isSessionActive ? 'bg-gray-500 cursor-not-allowed' : 'bg-green-500 hover:bg-green-600'
                } text-white`}
              >
                Begin Q&A
              </button>

              <button
                onClick={handleStop}
                disabled={!isSessionActive}
                className={`px-6 py-2 rounded-md ${
                  !isSessionActive ? 'bg-gray-500 cursor-not-allowed' : 'bg-red-500 hover:bg-red-600'
                } text-white`}
              >
                Stop
              </button>

              <span className="text-red-500 text-xl ml-auto">
                {String(Math.floor(time / 60)).padStart(2,'0')}:
                {String(time % 60).padStart(2,'0')}
              </span>
            </div>

            {/* Video */}
            <div
              className={`w-full aspect-video rounded-lg border border-gray-700 mb-4 overflow-hidden ${
                isSessionActive && videoRef.current?.src ? 'bg-black' : 'bg-[#1c1b2b]'
              }`}
            >
              <img ref={videoRef} alt="Live Feed" className="w-full h-full object-cover" />
            </div>

            {/* Sponsor images */}
            <div className="flex justify-center gap-8 mt-12">
              {['images/rbc.png', 'images/google.png', 'images/password.png'].map((img, index) => (
                <div
                  key={index}
                  className="w-36 h-36 rounded-full overflow-hidden relative hover:ring-2 hover:ring-green-500 transition-all bg-white p-2"
                >
                  <Image
                    src={`/${img}`}
                    alt={img.split('/').pop()?.split('.')[0] || ''}
                    fill
                    style={{ objectFit: 'contain' }}
              
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Transcript */}
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-white mb-2">Transcript</h2>
            <div className="bg-[#1c1b2b] p-4 rounded-md min-h-[300px] overflow-y-auto text-white">
              {transcript.map((entry, i) => (
                <div key={i} className="mb-2">
                  <strong>{entry.speaker}:</strong> {entry.text}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
