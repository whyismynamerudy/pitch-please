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
    {
      initialX: 10,
      translateX: 10,
      duration: 7,
      repeatDelay: 3,
      delay: 2,
    },
    {
      initialX: 600,
      translateX: 600,
      duration: 3,
      repeatDelay: 3,
      delay: 4,
    },
    {
      initialX: 100,
      translateX: 100,
      duration: 7,
      repeatDelay: 7,
      className: "h-6",
    },
    {
      initialX: 400,
      translateX: 400,
      duration: 5,
      repeatDelay: 14,
      delay: 4,
    },
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