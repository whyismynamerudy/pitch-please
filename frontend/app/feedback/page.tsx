'use client'

import { motion } from 'framer-motion'
import Image from 'next/image'
import { useState } from 'react'
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"

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
  className="bg-white/5 rounded-lg overflow-hidden cursor-pointer"
>
  <motion.div layout className="p-4">
    <div className="flex items-center gap-4">
      {/* Ensure the logo image is not cut off */}
      <div className="w-[100px] h-[100px] flex-shrink-0">
        <Image
          src={company.logo || "/placeholder.svg"}
          alt={`${company.name} logo`}
          width={100}
          height={100}
          className="rounded-full object-cover"
        />
      </div>
      <h3 className="text-3xl font-semibold">{company.name}</h3>
    </div>

    {/* Expanded View - Always Rendered */}
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="mt-4 space-y-6"
    >
      {/* Expanded image */}
      <div className="relative w-full h-[200px]">
        <Image
          src={company.expandedImage || "/placeholder.svg"}
          alt={`${company.name} expanded view`}
          fill
          className="object-contain rounded-lg"
        />
      </div>

      {/* Sections */}
      <div className="grid gap-4">
        {Object.entries(company.sections).map(([key, value]) => (
          <div key={key}>
            <h4 className="text-lg font-medium capitalize mb-2">
              {key.replace(/([A-Z])/g, " $1")}
            </h4>
            <p className="text-gray-300">{value}</p>
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
      
      {/* Content wrapper with higher z-index */}
      <div className="relative z-10">
        {/* Centered Navbar */}
        <nav className="flex justify-center items-center p-6">
          <div className="w-full max-w-7xl flex justify-between items-center px-4">
            <a href="/" className="text-white text-xl font-medium hover:text-purple-400 transition-colors">
              Home
            </a>
          </div>
        </nav>

        {/* Main content */}
        <div className="max-w-[90%] mx-auto px-4">
          <h1 className="text-6xl font-bold mb-12 bg-gradient-to-r from-purple-400 to-purple-600 text-transparent bg-clip-text text-center">
            Feedback
          </h1>

           {/* Updated Log Section */}
      <div className="mb-12">
        <h2 className="text-4xl font-semibold mb-4">Log</h2>
        <div className="backdrop-blur-md bg-white/10 rounded-lg p-4 h-[150px] overflow-y-auto shadow-xl border border-white/20">
          {Array(6)
            .fill(
              'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
            )
            .map((text, index) => (
              <p key={index} className="mb-2 last:mb-0">{text}</p>
            ))}
        </div>
      </div>

          {/* Grid layout for cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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


