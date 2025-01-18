'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import Image from "next/image"

export default function PitchPage() {
  const [isRecording, setIsRecording] = useState(false)
  const [timeLeft, setTimeLeft] = useState(15)
  const videoRef = useRef<HTMLVideoElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  useEffect(() => {
    let interval: NodeJS.Timeout
    
    if (isRecording && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft((prev) => prev - 1)
      }, 1000)
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [isRecording, timeLeft])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
      setTimeLeft(15)
    } catch (err) {
      console.error("Error accessing camera:", err)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && streamRef.current) {
      mediaRecorderRef.current.stop()
      streamRef.current.getTracks().forEach(track => track.stop())
      setIsRecording(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#1a1a2e] text-white p-6">
      <h1 className="text-6xl font-bold text-center mb-8">PITCH</h1>
      
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <div className="flex gap-4 mb-4">
            <Button 
              onClick={startRecording}
              disabled={isRecording}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Record
            </Button>
            <Button 
              onClick={stopRecording}
              disabled={!isRecording}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Stop
            </Button>
            <span className="ml-auto text-2xl font-mono text-red-500">
              {String(Math.floor(timeLeft / 60)).padStart(2, '0')}:
              {String(timeLeft % 60).padStart(2, '0')}
            </span>
          </div>

          <Card className="bg-black/20 aspect-video relative overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
            />
          </Card>

          <div className="flex justify-center gap-8 mt-8">
            <Image
              src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/rbc-v1zG1cmLVCubeRzsRYzLeRnURUSSet.png"
              alt="RBC Logo"
              width={100}
              height={100}
              className="rounded-full transition-all hover:ring-4 hover:ring-green-500"
            />
            <Image
              src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/google-iekbmsyzkER1MUmpTuU6Dve8e2BSGy.png"
              alt="Google Logo"
              width={100}
              height={100}
              className="rounded-full transition-all hover:ring-4 hover:ring-green-500"
            />
            <Image
              src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/password-MVFPo7UpEXNjSEdS1Ocf8KNwXdEtEr.png"
              alt="Password Logo"
              width={100}
              height={100}
              className="rounded-full transition-all hover:ring-4 hover:ring-green-500"
            />
          </div>
        </div>

        <Card className="bg-black/20 p-4">
          <h2 className="text-2xl font-bold mb-4">Transcript</h2>
          <p className="text-gray-300">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
          </p>
        </Card>
      </div>
    </div>
  )
}

