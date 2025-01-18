'use client'
import { useState, useEffect, useRef } from 'react'
import Image from 'next/image'

export default function PitchPage() {
  const [time, setTime] = useState(15)
  const [isRecording, setIsRecording] = useState(false)
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isRecording && time > 0) {
      interval = setInterval(() => {
        setTime((prevTime) => prevTime - 1)
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isRecording, time])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      setVideoStream(stream)
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setIsRecording(true)
      setTime(15)
    } catch (err) {
      console.error('Error accessing camera:', err)
    }
  }

  const stopRecording = () => {
    if (videoStream) {
      videoStream.getTracks().forEach(track => track.stop())
      setVideoStream(null)
    }
    setIsRecording(false)
  }

  return (
    <div className="min-h-screen bg-[#14121f]">
      <div className="max-w-[1400px] mx-auto px-8">
        
        {/* Navigation */}
        <nav className="py-6">
          <a href="/" className="text-white text-xl font-medium">
            Home
          </a>
        </nav>
        <br></br>
        <br></br>

        {/* Title with gradient */}
        <h1 className="text-6xl font-bold bg-gradient-to-r from-[#6366f1] to-[#4f46e5] bg-clip-text text-transparent mb-8">
          Pitch
        </h1>

        <div className="flex gap-8">
          {/* Left Section */}
          <div className="flex-1">
            {/* Buttons and Timer */}
            <div className="flex items-center gap-4 mb-4">
              <button
                onClick={startRecording}
                className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                Record
              </button>
              <button
                onClick={stopRecording}
                className="px-6 py-2 bg-red-500 text-white rounded-md hover:bg-red-600"
              >
                Stop
              </button>
              <span className="text-red-500 text-xl ml-auto">
                {String(Math.floor(time / 60)).padStart(2, '0')}:
                {String(time % 60).padStart(2, '0')}
              </span>
            </div>

            {/* Video Container */}
            <div className="w-full aspect-video bg-[#1c1b2b] rounded-lg border border-gray-700 mb-4 overflow-hidden">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
            </div>

            {/* Sponsor Images - Adjusted size and positioning */}
            <div className="flex justify-center gap-8 mt-12">
              {['images/rbc.png', 'images/google.png', 'images/password.png'].map((img, index) => (
                <div
                  key={index}
                  className="w-24 h-24 rounded-full overflow-hidden relative hover:ring-2 hover:ring-green-500 transition-all bg-white p-2"
                >
                  <Image
                    src={`/${img}`}
                    alt={img.split('/').pop()?.split('.')[0] || ''}
                    fill
                    style={{ objectFit: 'contain' }}
                    className="p-2"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Right Section - Transcript */}
          <div className="w-96">
            <div className="bg-[#1c1b2b] p-6 rounded-lg border border-gray-700 mt-[60px]">
              <h2 className="text-white text-2xl font-bold mb-4">Transcript</h2>
              <p className="text-gray-300">
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
                tempor incididunt ut labore et dolore magna aliqua.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 