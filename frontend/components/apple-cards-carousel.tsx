'use client'

import { motion } from "framer-motion"
import { useRef } from "react"

const cards = [
  {
    title: "Refine your pitch like a pro.",
    image: "/images/pitch.jpg"
  },
  {
    title: "See your pitch through every lens.",
    image: "/images/lens.jpg"
  },
  {
    title: "Turn critiques into opportunities.",
    image: "images/celebrate.jpg"
  }
]

export function AppleCardsCarousel() {
  const containerRef = useRef<HTMLDivElement>(null)

  const scrollLeft = () => {
    if (containerRef.current) {
      containerRef.current.scrollBy({ left: -700, behavior: "smooth" })
    }
  }

  const scrollRight = () => {
    if (containerRef.current) {
      containerRef.current.scrollBy({ left: 700, behavior: "smooth" })
    }
  }

  return (
    <div className="relative overflow-hidden px-8">
      {/* Carousel Container */}
      <div
        ref={containerRef}
        className="flex items-center gap-8 overflow-x-auto scroll-smooth px-4"
        style={{ scrollSnapType: "x mandatory" }}
      >
        {cards.map((card, index) => (
          <motion.div
            key={index}
            className="relative shrink-0 w-[70vw] max-w-[900px] cursor-pointer rounded-xl bg-white shadow-lg"
            style={{ scrollSnapAlign: "center" }}
            whileHover={{ scale: 1.02 }}
          >
            <div className="relative h-[500px] w-full overflow-hidden rounded-xl">
              <img
                src={card.image || "/placeholder.svg"}
                alt={card.title}
                className="h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-black/40" />
              <div className="absolute bottom-0 left-0 right-0 p-8">
                <h3 className="text-3xl font-bold text-white">{card.title}</h3>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Navigation Arrows */}
      <div className="absolute bottom-8 left-0 right-0 flex justify-between px-8">
        <button
          onClick={scrollLeft}
          className="p-4 bg-black/50 text-white rounded-full hover:bg-black/70"
        >
          &larr;
        </button>
        <button
          onClick={scrollRight}
          className="p-4 bg-black/50 text-white rounded-full hover:bg-black/70"
        >
          &rarr;
        </button>
      </div>
    </div>
  )
}
