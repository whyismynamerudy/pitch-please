"use client"

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const loadingMessages = [
  "Analyzing pitch...",
  "Individual judges contemplating...",
  "Judges arguing...",
  "Judges discussing...",
  "Judges reaching a consensus...",
  "Compiling feedback...",
  "Finalizing evaluation..."
];

export default function LoadingAnalysis() {
  const [currentMessage, setCurrentMessage] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessage((prev) => (prev + 1) % loadingMessages.length);
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="text-center space-y-6">
        <div className="relative w-24 h-24 mx-auto">
          <motion.div
            className="w-full h-full rounded-full border-4 border-t-purple-500 border-r-blue-500 border-b-indigo-500 border-l-violet-500"
            animate={{ rotate: 360 }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "linear"
            }}
          />
        </div>
        <motion.div
          key={loadingMessages[currentMessage]}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="text-xl text-white font-medium"
        >
          {loadingMessages[currentMessage]}
        </motion.div>
      </div>
    </div>
  );
}