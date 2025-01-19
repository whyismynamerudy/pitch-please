'use client'

import { motion } from 'framer-motion'
import Image from 'next/image'
import { useState } from 'react'
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import Link from 'next/link'


interface Company {
  id: string
  name: string
  logo: string
  expandedImage: string
  sections: {
    pace: string
    duration: string
    emotion: string
    speakingStyle: string
    improvement: string
  }
}

interface ExpandableCardProps {
  
  company: Company
  isExpanded: boolean
  onExpand: () => void
}

export function ExpandableCard({ company, isExpanded, onExpand }: ExpandableCardProps) {
  return (
    <motion.div
      layout
      onClick={onExpand}
      className="bg-white/5 backdrop-blur-md rounded-lg overflow-hidden cursor-pointer hover:bg-white/10 transition-colors border border-white/10"
    >
      <motion.div layout className="p-6">
        {/* Company Header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-[80px] h-[80px] flex-shrink-0">
            <Image
              src={company.logo || "/placeholder.svg"}
              alt={`${company.name} logo`}
              width={80}
              height={80}
              className="rounded-full object-cover"
            />
          </div>
          <div>
            <h3 className="text-2xl font-semibold">{company.name}</h3>
            {/* Overall Score */}
            <div className="mt-2">
              <div className="inline-flex items-center justify-center bg-purple-500/20 rounded-full px-4 py-1">
                <span className="text-purple-300 font-medium">Score: 8.5/10</span>
              </div>
            </div>
          </div>
        </div>

        {/* Expanded Content */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          {/* Category Scores Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {Object.entries(company.sections).map(([key]) => (
              <div key={key} className="bg-white/5 rounded-lg p-4 text-center">
                <h4 className="text-sm text-purple-300 capitalize mb-2">
                  {key.replace(/([A-Z])/g, " $1")}
                </h4>
                <span className="text-2xl font-bold">9.0</span>
              </div>
            ))}
          </div>

          {/* Detailed Feedback */}
          <div className="space-y-4">
            {Object.entries(company.sections).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg p-4">
                <h4 className="text-lg font-medium text-purple-300 capitalize mb-2">
                  {key.replace(/([A-Z])/g, " $1")}
                </h4>
                <p className="text-gray-300 leading-relaxed">{value}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  )
}

export default function FeedbackPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const companies = [
    {
      id: '1',
      name: 'RBC',
      logo: '/images/rbc.png',
      expandedImage: '/images/rbcc.png',
      sections: {
        pace: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        duration: 'Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
        emotion: 'Ut enim ad minim veniam, quis nostrud exercitation ullamco.',
        speakingStyle: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        improvement: 'Sed do eiusmod tempor incididunt ut labore.'
      }
    },
    {
      id: '2',
      name: 'Google',
      logo: '/images/google.png',
      expandedImage: '/images/google2.webp',
      sections: {
        pace: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        duration: 'Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
        emotion: 'Ut enim ad minim veniam, quis nostrud exercitation ullamco.',
        speakingStyle: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        improvement: 'Sed do eiusmod tempor incididunt ut labore.'
      }
    },
    {
      id: '3',
      name: '1Password',
      logo: '/images/password.png',
      expandedImage: '/images/passwordd.png',
      sections: {
        pace: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        duration: 'Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
        emotion: 'Ut enim ad minim veniam, quis nostrud exercitation ullamco.',
        speakingStyle: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        improvement: 'Sed do eiusmod tempor incididunt ut labore.'
      }
    }
  ]

  return (
    <div className="relative min-h-screen bg-black text-white">

      <div className="fixed inset-0 z-0">
        <BackgroundBeamsWithCollision />
      </div>
      
      <div className="relative z-10">
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
        <div className="max-w-7xl mx-auto px-4 py-8">
          <h1 className="text-6xl font-bold mb-12 bg-gradient-to-r from-purple-400 to-purple-600 text-transparent bg-clip-text text-center">
            Interview Feedback
          </h1>

          {/* General Consensus Section */}
          <div className="mb-12">
            <h2 className="text-3xl font-semibold mb-6 text-center">Overall Performance</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 text-center">
                <h3 className="text-xl text-purple-300 mb-2">Average Score</h3>
                <span className="text-4xl font-bold">8.7/10</span>
              </div>
              <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 text-center">
                <h3 className="text-xl text-purple-300 mb-2">Interviews</h3>
                <span className="text-4xl font-bold">3</span>
              </div>
              <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 text-center">
                <h3 className="text-xl text-purple-300 mb-2">Success Rate</h3>
                <span className="text-4xl font-bold">92%</span>
              </div>
            </div>
            
            {/* Judges Consensus */}
            <div className="bg-white/5 backdrop-blur-md rounded-lg p-6">
              <h3 className="text-2xl font-semibold mb-4">Judges Consensus</h3>
              <p className="text-gray-300 leading-relaxed">
                Outstanding performance across all interviews. Demonstrated excellent technical knowledge
                and communication skills. Particularly strong in problem-solving and system design.
                Recommended areas for improvement include deeper dive into distributed systems concepts.
              </p>
            </div>
          </div>

          {/* Activity Log */}
          <div className="mb-12">
            <h2 className="text-3xl font-semibold mb-4">Activity Log</h2>
            <div className="backdrop-blur-md bg-white/5 rounded-lg p-4 h-[150px] overflow-y-auto border border-white/10">
              {Array(6)
                .fill(
                  'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
                )
                .map((text, index) => (
                  <p key={index} className="mb-2 last:mb-0">{text}</p>
                ))}
            </div>
          </div>

          {/* Company Feedback Cards */}
          <h2 className="text-3xl font-semibold mb-6">Detailed Company Feedback</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {companies.map((company) => (
              <ExpandableCard
                key={company.id}
                company={company}
                isExpanded={expandedId === company.id}
                onExpand={() => setExpandedId(expandedId === company.id ? null : company.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}


