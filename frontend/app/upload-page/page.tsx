'use client'

import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function UploadPage() {
  return (
    <div className="min-h-screen relative" style={{ background: 'rgb(22, 14, 34)' }}>
      {/* Background Beams */}
      <div className="absolute inset-0 z-0">
        <BackgroundBeamsWithCollision />
      </div>

      {/* Foreground Content */}
      <div className="relative z-10">
        {/* Centered Navbar */}
        <nav className="flex justify-center items-center p-6">
          <div className="w-full max-w-7xl flex justify-between items-center px-4">
            <a href="/" className="text-white text-xl font-medium">
              Home
            </a>
          </div>
        </nav>

        {/* Main Content */}
        <div className="flex flex-col items-center justify-center min-h-[80vh] p-4">
          <Card className="w-full max-w-3xl bg-[#1c1b2b] border-gray-800">
            <CardHeader>
              <CardTitle className="text-4xl font-bold bg-gradient-to-r from-[#6366f1] to-[#4f46e5] bg-clip-text text-transparent">
                Upload
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Rubric Section */}
              <div className="space-y-3">
                <Label htmlFor="rubric" className="text-gray-200 text-lg">
                  Rubric
                </Label>
                <div className="relative">
                  <input
                    id="rubric"
                    type="file"
                    className="block w-full text-white file:bg-[#2a2937] file:text-white file:px-4 file:py-2 file:rounded-md file:cursor-pointer"
                  />
                </div>
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
