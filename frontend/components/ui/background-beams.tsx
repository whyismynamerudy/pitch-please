"use client"
import { useEffect, useRef, memo } from "react"

export const BackgroundBeams = memo(() => {
  return (
    <div className="absolute inset-0 opacity-30 [mask-image:radial-gradient(100%_100%_at_top_center,black,transparent)]">
      <div className="absolute inset-0 bg-gradient-to-r from-grey-500/30 via-purple-500/30 to-blue-500/30 backdrop-blur-[100px]" />
    </div>
  )
})

BackgroundBeams.displayName = "BackgroundBeams"

