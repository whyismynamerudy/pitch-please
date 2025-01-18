'use client'

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function UploadPage() {
  return (
    <div className="min-h-screen bg-[#14121f] flex flex-col items-center justify-center p-4">
      <Card className="w-full max-w-md bg-[#1c1b2b] border-gray-800">
        <CardHeader>
          <CardTitle className="text-4xl font-bold bg-gradient-to-r from-[#6366f1] to-[#4f46e5] bg-clip-text text-transparent">
            Upload
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="rubric" className="text-gray-200">
              Rubric
            </Label>
            <Input
              id="rubric"
              type="file"
              className="bg-[#2a2937] border-gray-700 text-gray-200"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="sponsors" className="text-gray-200">
              Sponsors
            </Label>
            <Input
              id="sponsors"
              type="text"
              placeholder="Enter sponsors"
              className="bg-[#2a2937] border-gray-700 text-gray-200"
            />
          </div>
          <Button 
            className="w-full bg-gradient-to-r from-[#6366f1] to-[#4f46e5] hover:opacity-90 transition-opacity"
          >
            Submit
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

