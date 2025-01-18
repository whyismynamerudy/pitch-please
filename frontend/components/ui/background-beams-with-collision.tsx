"use client";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import React, { useRef, useState, useEffect } from "react";

export const BackgroundBeamsWithCollision = ({
  className,
}: {
  className?: string;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  const beams = [
    
        { initialX: 50, translateX: 50, duration: 6, repeatDelay: 0.5, delay: 0 },
        { initialX: 200, translateX: 200, duration: 7, repeatDelay: 1, delay: 0.2 },
        { initialX: 400, translateX: 400, duration: 8, repeatDelay: 0.5, delay: 0.5 },
        { initialX: 600, translateX: 600, duration: 6, repeatDelay: 0.3, delay: 0 },
        { initialX: 800, translateX: 800, duration: 7, repeatDelay: 0.4, delay: 0.7 },
        { initialX: 1000, translateX: 1000, duration: 6, repeatDelay: 0.2, delay: 0.3 },
        { initialX: 1200, translateX: 1200, duration: 9, repeatDelay: 0.6, delay: 1 },
        { initialX: 1400, translateX: 1400, duration: 8, repeatDelay: 0.5, delay: 0.8 },
        { initialX: 1600, translateX: 1600, duration: 5, repeatDelay: 0.7, delay: 0.4 },
        { initialX: 1800, translateX: 1800, duration: 6, repeatDelay: 0.5, delay: 0.1 },
  

  ];

  return (
    <div
      ref={parentRef}
      className={cn(
        "h-screen bg-[rgb(22,14,34)] relative flex items-center w-full justify-center overflow-hidden",
        className
      )}
    >
      {beams.map((beam, idx) => (
        <motion.div
          key={idx}
          initial={{
            translateY: "-100vh",
            translateX: beam.initialX,
          }}
          animate={{
            translateY: "100vh",
            translateX: beam.translateX,
          }}
          transition={{
            duration: beam.duration,
            repeat: Infinity,
            repeatType: "loop",
            ease: "linear",
            delay: beam.delay,
            repeatDelay: beam.repeatDelay,
          }}
          className={cn(
            "absolute left-0 top-0 h-32 w-[1px] bg-gradient-to-b from-transparent via-violet-500 to-transparent",
            beam.className
          )}
        />
      ))}
    </div>
  );
}; 