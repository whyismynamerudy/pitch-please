import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import { Button } from "@/components/ui/button"
import { AppleCardsCarousel } from "@/components/apple-cards-carousel"
import Link from 'next/link'
import Image from 'next/image'

export default function Home() {
  return (
    <div className="min-h-screen relative" style={{ background: 'rgb(65, 65, 71)' }}>
      {/* Background Beams */}
      <div className="absolute inset-0 z-0">
        <BackgroundBeamsWithCollision />
      </div>

      <div className="relative z-10">
        {/* Navbar */}
        <nav className="flex justify-end p-6">
          <div className="border border-transparent bg-gradient-to-r from-violet-500 via-blue-500 to-indigo-500 rounded-lg p-[1px]">
            <div className="bg-[rgb(40,40,45)] rounded-lg px-6 py-3">
              <a href="/" className="text-white text-xl font-medium hover:opacity-80 transition-opacity">
                Home
              </a>
            </div>
          </div>
        </nav>

        {/* Hero Section with Side-by-Side Layout */}
        <div className="max-w-7xl mx-auto pt-20 pb-16">
          <div className="flex flex-col md:flex-row items-center gap-12">
            {/* Left Column - Text Content */}
            <div className="flex-1 space-y-6">
              <br>
              </br>
              <br></br>
              <br></br>
              <br></br>
              <h1 className="text-5xl md:text-7xl font-bold text-white leading-tight">
                Deliver pitches that <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-500 via-blue-500 to-indigo-500">win</span>
              </h1>
              <p className="text-lg md:text-xl text-gray-300 leading-relaxed">
                Learn from curated, AI-driven insights to refine your pitch into a winner. Whether you're aiming to win a hackathon or join YC Combinator, our tools ensure your ideas resonate and make an impact.
              </p>
              <div className="pt-4">
                <Link href="/upload-page">
                  <Button className="bg-gradient-to-r from-violet-500/90 via-blue-500/90 to-indigo-500/90 text-white text-lg px-8 py-4 rounded-xl hover:opacity-90 transition-opacity">
                    Get Started
                  </Button>
                </Link>
              </div>
            </div>

            {/* Right Column - Image Grid */}
            <div className="flex-1">
              <br></br>
              <br></br>
              <br></br>
              <br></br>
              <br></br>
              <br></br>

              <div className="grid grid-cols-2 gap-4">
                <Image 
                  src="/images/uofthacks.jpg" 
                  alt="Feature 1" 
                  width={400} 
                  height={300} 
                  className="rounded-xl w-full aspect-video object-cover hover:scale-105 transition-transform"
                />
                <Image 
                  src="/images/image2.png" 
                  alt="Feature 2" 
                  width={400} 
                  height={300} 
                  className="rounded-xl w-full aspect-video object-cover hover:scale-105 transition-transform"
                />
                <Image 
                  src="/images/image3.png" 
                  alt="Feature 3" 
                  width={400} 
                  height={300} 
                  className="rounded-xl w-full aspect-video object-cover hover:scale-105 transition-transform"
                />
                <Image 
                  src="/images/mlh.jpg" 
                  alt="Feature 4" 
                  width={400} 
                  height={300} 
                  className="rounded-xl w-full aspect-video object-cover hover:scale-105 transition-transform"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action Section */}
        <div className="text-center max-w-4xl mx-auto px-4 py-20">
          <br></br>
          <br></br>
          <br></br>
          <br></br>
          <br></br>
          <br></br>
          <br></br>

          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Perfecting your pitch is <span className="bg-clip-text text-transparent bg-gradient-to-r from-violet-500 via-blue-500 to-indigo-500">hard</span>.
          </h2>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">Stop guessing. </h2>
          <p className="text-lg md:text-xl text-gray-300 mb-8">
            Are you a startup founder, hackathon participant, or aspiring YC applicant struggling to craft a pitch that stands out? Save time and let us help.
          </p>
          <p className="text-xl text-white font-medium">We've got you covered.</p>
        </div>

        {/* Cards Section */}
        <div className="py-20">
          <AppleCardsCarousel />
        </div>
      </div>
    </div>
  )
}
