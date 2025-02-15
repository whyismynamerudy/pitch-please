'use client'

import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { FileUpload } from "@/components/ui/file-upload"
import { useState } from "react"

export default function UploadPage() {
  const router = useRouter()
  const [files, setFiles] = useState<File[]>([])

  const handleSubmit = () => {
    console.log('Files to upload:', files)
    router.push('/pitch-page')
  }

  return (
    <div className="min-h-screen relative" style={{ background: 'rgb(22, 14, 34)' }}>
      {/* Background Beams */}
      <div className="absolute inset-0 z-0">
        <BackgroundBeamsWithCollision />
      </div>

      {/* Foreground Content */}
      <div className="relative z-10">
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

        {/* Main Content */}
        <div className="flex flex-col items-center justify-center min-h-[80vh] p-4">
          <Card className="w-full max-w-3xl bg-[#1c1b2b] border-gray-800">
            <CardHeader>
              <h1 className="text-5xl md:text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-500 via-blue-500 to-indigo-500">
                Upload
              </h1>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Rubric Section */}
              <div className="space-y-3">
                <Label htmlFor="rubric" className="text-gray-200 text-lg">
                  Rubric
                </Label>
                <FileUpload
                  onChange={(files) => {
                    setFiles(files)
                    console.log('Files changed:', files)
                  }}
                />
              </div>
              {/* Sponsors Section */}
              <div className="space-y-3">
                <Label htmlFor="sponsors" className="text-gray-200 text-lg">
                  Sponsors
                </Label>
                <Input
                  id="sponsors"
                  type="text"
                  placeholder="Enter sponsors"
                  className="bg-[#2a2937] border-gray-700 text-gray-200 text-lg"
                />
              </div>
              {/* Submit Button */}
              <Button
                onClick={handleSubmit}
                className="w-full bg-gradient-to-r from-[#6366f1] to-[#4f46e5] hover:opacity-90 transition-opacity text-white text-lg font-medium"
              >
                Submit
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
