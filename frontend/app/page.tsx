import { BackgroundBeams } from "@/components/ui/background-beams"
import { Button } from "@/components/ui/button"
import { AppleCardsCarousel } from "@/components/apple-cards-carousel"

export default function Home() {
  return (
    <div className="min-h-screen relative" style={{ background: 'rgb(22, 14, 34)' }}>
      <BackgroundBeams />
      <div className="relative z-10">
        {/* Navbar */}
        <nav className="flex justify-between items-center p-6">
          <a href="/" className="text-white text-xl">
            Home
          </a>
         
        </nav>

        {/* Hero Section */}
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
          <h1 className="text-white text-4xl md:text-6xl font-bold mb-4">
            The best judge of your pitch?
          </h1>
          <h1 className="text-white text-4xl md:text-6xl font-bold mb-8">
            Pitch Please.
          </h1>
            <Button
          className="bg-white text-black rounded-full px-8 py-4 shadow-md hover:bg-white/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black transition-all"
        >
         <p className="text-black">Get Started</p>
        </Button>
        </div>

        {/* Cards Section */}
        <div className="py-20">
          <AppleCardsCarousel />
        </div>
      </div>
    </div>
  )
}

