"use client"

import { motion } from 'framer-motion'
import Image from 'next/image'
import { useState, useEffect } from 'react'
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import Link from 'next/link'

// Define interfaces for our data structure
interface Score {
  practicality_and_impact: number;
  pitching: number;
  design: number;
  completion: number;
  theme_and_originality: number;
}

interface Feedback {
  practicality_and_impact: string;
  pitching: string;
  design: string;
  completion: string;
  theme_and_originality: string;
}

interface JudgeEvaluation {
  judge_name: string;
  company: string;
  scores: Score;
  feedback: Feedback;
  overall_feedback: string;
  key_points: string[];
}

interface ConsensusEvaluation {
  final_scores: Score;
  discussion_summary: string;
  detailed_discussions: Record<string, any>;
}

interface MainEvaluation {
  individual_evaluations: JudgeEvaluation[];
  consensus_evaluation: ConsensusEvaluation;
  meta_analysis: Record<string, any>;
}

interface EvaluationResults {
  main_evaluation: MainEvaluation;
  sponsor_challenges: Record<string, any>;
}

interface AnalysisData {
  success: boolean;
  evaluation_results: EvaluationResults;
  captured_output: string;
  input_data: {
    wpm: number;
    time: string;
    emotions: Record<string, number>;
  };
}

interface AD {
  analysis_result: Record<string, any>
  evaluation_response: AnalysisData
}

interface Company {
  id: string;
  name: string;
  logo: string;
  expandedImage: string;
  sections: Score;  // Change this from Record<string, number> to Score
  feedback: Feedback;  // Change this from Record<string, string> to Feedback
  keyPoints: string[];
}

interface ExpandableCardProps {
  company: Company;
  isExpanded: boolean;
  onExpand: () => void;
}

function ExpandableCard({ company, isExpanded, onExpand }: ExpandableCardProps) {
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
              src={company.logo}
              alt={`${company.name} logo`}
              width={80}
              height={80}
              className="rounded-full object-cover"
            />
          </div>
          <div>
            <h3 className="text-2xl font-semibold">{company.name}</h3>
            <div className="mt-2">
              <div className="inline-flex items-center justify-center bg-purple-500/20 rounded-full px-4 py-1">
                <span className="text-purple-300 font-medium">
                  Average: {(Object.values(company.sections).reduce((a, b) => a + b, 0) / Object.keys(company.sections).length).toFixed(1)}
                </span>
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
            {Object.entries(company.sections).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg p-4 text-center">
                <h4 className="text-sm text-purple-300 capitalize mb-2">
                  {key.replace(/([A-Z])/g, " $1")}
                </h4>
                <span className="text-2xl font-bold">{value.toFixed(1)}</span>
              </div>
            ))}
          </div>

          {/* Detailed Feedback */}
          <div className="space-y-4">
            {Object.entries(company.feedback).map(([key, value]) => (
              <div key={key} className="bg-white/5 rounded-lg p-4">
                <h4 className="text-lg font-medium text-purple-300 capitalize mb-2">
                  {key.replace(/([A-Z])/g, " $1").replace(/_/g, " ")}
                </h4>
                <p className="text-gray-300 leading-relaxed">{value}</p>
              </div>
            ))}
          </div>

          {/* Key Points */}
          <div className="bg-white/5 rounded-lg p-4">
            <h4 className="text-lg font-medium text-purple-300 mb-2">Key Points</h4>
            <ul className="list-disc list-inside space-y-2">
              {company.keyPoints.map((point: string, index: number) => (
                <li key={index} className="text-gray-300">{point}</li>
              ))}
            </ul>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  )
}

export default function FeedbackPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [analysisData, setAnalysisData] = useState<AD | null>(null)
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadTestData = async () => {
    try {
      const response = await fetch('/hi.json');
      const data = await response.json();
      setAnalysisData(data);
    } catch (error) {
      console.error('Error loading test data:', error);
      setError('Error loading test data');
    }
  };

  useEffect(() => {
    try {
      // Retrieve data from localStorage
      const storedData = localStorage.getItem('pitchAnalysis');
      if (storedData) {
        const parsedData = JSON.parse(storedData) as AD;
        setAnalysisData(parsedData);
        // Clean up localStorage after retrieving the data
        localStorage.removeItem('pitchAnalysis');
      } else {
        setError('No analysis data found. Please complete a pitch session first.');
      }
    } catch (e) {
      setError('Error loading analysis data. Please try again.');
      console.error('Error parsing analysis data:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Transform judges' evaluations into company data format
  const companies: Company[] = analysisData ? analysisData.evaluation_response.evaluation_results.main_evaluation.individual_evaluations.map((evaluation) => ({
    id: evaluation.judge_name,
    name: evaluation.company,
    logo: `/images/${evaluation.judge_name.toLowerCase().replace(' ', '')}.png`,
    expandedImage: `/images/${evaluation.judge_name.toLowerCase().replace(' ', '')}2.png`,
    sections: evaluation.scores,
    feedback: evaluation.feedback,
    keyPoints: evaluation.key_points
  })) : [];

  // Calculate overall metrics
  const consensusScores = analysisData?.evaluation_response.evaluation_results.main_evaluation.consensus_evaluation.final_scores
  const averageScore = consensusScores ? 
    Object.values(consensusScores).reduce((a, b) => a + b, 0) / Object.keys(consensusScores).length : 0

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
          <div className="flex justify-center items-center gap-4 mb-12">
            <h1 className="text-6xl font-bold bg-gradient-to-r from-purple-400 to-purple-600 text-transparent bg-clip-text text-center">
              Interview Feedback
            </h1>
            <button
              onClick={loadTestData}
              className="px-4 py-2 bg-purple-500 rounded-lg hover:bg-purple-600 transition-colors"
            >
              Load Test Data
            </button>
          </div>

          {/* General Consensus Section */}
          <div className="mb-12">
            <h2 className="text-3xl font-semibold mb-6 text-center">Overall Performance</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 text-center">
                <h3 className="text-xl text-purple-300 mb-2">Average Score</h3>
                <span className="text-4xl font-bold">{averageScore.toFixed(1)}/10</span>
              </div>
              <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 text-center">
                <h3 className="text-xl text-purple-300 mb-2">Judges</h3>
                <span className="text-4xl font-bold">{companies.length}</span>
              </div>
              <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 text-center">
                <h3 className="text-xl text-purple-300 mb-2">Success Rate</h3>
                <span className="text-4xl font-bold">
                  {((averageScore / 10) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            
            {/* Judges Consensus */}
            <div className="bg-white/5 backdrop-blur-md rounded-lg p-6">
              <h3 className="text-2xl font-semibold mb-4">Judges Consensus</h3>
              <p className="text-gray-300 leading-relaxed">
                {analysisData?.evaluation_response.evaluation_results.main_evaluation.consensus_evaluation.discussion_summary}
              </p>
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