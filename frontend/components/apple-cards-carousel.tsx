'use client'

import { motion } from "framer-motion"
import { useRef, useState } from "react"

const cards = [
  {
    title: "Refine your pitch like a pro.",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/pexels-paul-loh-65233-233698.jpg-rnXcaYMQ8C68mv1JF0bpfu2eBR7LKY.jpeg"
  },
  {
    title: "See your pitch through every lens.",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/pexels-hikaique-65438.jpg-pDAljQMcsDf6flwxhn9oaYndSagRHa.jpeg"
  },
  {
    title: "Turn critiques into opportunities.",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/pexels-introspectivedsgn-17716169.jpg-Ff7Ta2NTFK67FPqLAXGzibYEnGTROw.jpeg"
  }
]

export function AppleCardsCarousel() {
  const [activeCard, setActiveCard] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  return (
    <div className="overflow-hidden px-8">
      <div ref={containerRef} className="flex items-start justify-center gap-4 px-4">
        {cards.map((card, index) => (
          <motion.div
            key={index}
            className={`relative shrink-0 cursor-pointer rounded-xl bg-white shadow-lg transition-all ${
              activeCard === index ? "w-full md:w-3/4" : "w-3/4 md:w-2/3"
            }`}
            animate={{
              scale: activeCard === index ? 1 : 0.9,
              opacity: activeCard === index ? 1 : 0.6
            }}
            onClick={() => setActiveCard(index)}
          >
            <div className="relative h-[400px] w-full overflow-hidden rounded-xl">
              <img
                src={card.image || "/placeholder.svg"}
                alt={card.title}
                className="h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-black/40" />
              <div className="absolute bottom-0 left-0 right-0 p-8">
                <h3 className="text-2xl font-bold text-white">{card.title}</h3>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

