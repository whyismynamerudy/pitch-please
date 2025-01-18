import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import { Button } from "@/components/ui/button"
import { AppleCardsCarousel } from "@/components/apple-cards-carousel"
export default function Home() {
  return (
    <div className="min-h-screen relative" style={{ background: 'rgb(22, 14, 34)' }}>
      {/* Background Beams */}
      <div className="absolute inset-0 z-0">
        <BackgroundBeamsWithCollision />
      </div>

      <div className="relative z-10">
        {/* Centered Navbar */}
        <nav className="flex justify-center items-center p-6">
          <div className="w-full max-w-7xl flex justify-between items-center px-4">
            <a href="/" className="text-white text-xl font-medium">
              Home
            </a>
            <Button className="bg-white text-[rgb(22,14,34)] hover:bg-white/90">
              Get Started
            </Button>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
          <h1 className="text-white text-4xl md:text-6xl font-bold mb-4">
            Who&apos;s the best judge of your pitch?
          </h1>
          <h2 className="text-4xl md:text-6xl font-bold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-violet-500 via-purple-500 to-indigo-500">
            Pitch Please.
          </h2>
        </div>

        {/* Cards Section */}
        <div className="py-20">
          <AppleCardsCarousel />
        </div>
      </div>
    </div>
  )
}
