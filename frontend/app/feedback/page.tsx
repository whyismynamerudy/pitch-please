"use client"

import { motion } from 'framer-motion'
import Image from 'next/image'
import { useState, useEffect } from 'react'
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import Link from 'next/link'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

// Define interfaces for our data structure
interface Score {
  practicality_and_impact: number;
  pitching: number;
  design: number;
  completion: number;
  theme_and_originality: number;
}

interface hi {
  logo: string;
  expandedImage: string;
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
  // Get the correct images based on company name
  const getCompanyImages = (companyName: string) => {
    switch (companyName) {
      case 'Royal Bank of Canada':
        return {
          logo: '/images/rbc.png',
          banner: '/images/rbcc.png'
        };
      case 'Google':
        return {
          logo: '/images/google.png',
          banner: '/images/google2.webp'
        };
      case '1Password':
        return {
          logo: '/images/password.png',
          banner: '/images/passwordd.png'
        };
      default:
        return {
          logo: '/images/rbc.png',
          banner: '/images/rbcc.png'
        };
    }
  };

  const companyImages = getCompanyImages(company.name);
  const scoreData = Object.entries(company.sections).map(([key, value]) => ({
    name: key.replace(/([A-Z])/g, ' $1').trim(),
    value: value
  }));

  return (
    <motion.div
      layout
      onClick={onExpand}
      className={`bg-white/5 backdrop-blur-md rounded-lg overflow-hidden cursor-pointer transition-all duration-500 ${
        isExpanded ? 'col-span-2' : ''
      }`}
    >
      <motion.div layout className="p-6">
        {/* Company Header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-[80px] h-[80px] flex-shrink-0">
            <Image
              src={companyImages.logo}
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

        {isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="space-y-8"
          >
            {/* Expanded Header Image */}
            <div className="relative h-[200px] w-full rounded-lg overflow-hidden">
              <Image
                src={companyImages.banner}
                alt={`${company.name} banner`}
                fill
                className="object-cover"
              />
            </div>

            {/* Scores Chart */}
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scoreData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis dataKey="name" stroke="#fff" />
                  <YAxis stroke="#fff" domain={[0, 10]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  />
                  <Bar dataKey="value" fill="#8884d8">
                    {scoreData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={`hsl(${index * 50}, 70%, 60%)`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Feedback Sections */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {Object.entries(company.feedback).map(([key, value]) => (
                <div key={key} className="bg-white/5 rounded-lg p-6">
                  <h4 className="text-lg font-medium text-purple-300 capitalize mb-3">
                    {key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}
                  </h4>
                  <p className="text-gray-300 leading-relaxed">{value}</p>
                </div>
              ))}
            </div>

            {/* Key Points */}
            <div className="bg-white/5 rounded-lg p-6">
              <h4 className="text-lg font-medium text-purple-300 mb-4">Key Points</h4>
              <ul className="space-y-3">
                {company.keyPoints.map((point, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="text-purple-400 mt-1">•</span>
                    <span className="text-gray-300">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}

function AnalysisSection({ analysisData }: { analysisData: AD | null }) {
  if (!analysisData) return null;

  const { emotions, wpm, time, transcript } = analysisData.analysis_result;
  
  // Transform emotions data for pie chart
  const emotionsData = Object.entries(emotions).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: value
  }));

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#a4de6c'];

  return (
    <div className="mb-12 space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Enhanced Speech Metrics */}
        <div className="bg-white/5 backdrop-blur-md rounded-lg p-6">
          <h3 className="text-2xl font-semibold mb-6">Speech Metrics</h3>
          <div className="grid grid-cols-2 gap-8">
            <div className="relative">
              <div className="absolute inset-0 bg-purple-500/20 rounded-full animate-pulse" />
              <div className="relative text-center p-6">
                <div className="text-4xl font-bold mb-2">{wpm.toFixed(0)}</div>
                <p className="text-purple-300">Words per Minute</p>
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/20 rounded-full animate-pulse" />
              <div className="relative text-center p-6">
                <div className="text-4xl font-bold mb-2">{time}</div>
                <p className="text-blue-300">Duration</p>
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Emotions Chart */}
        <div className="bg-white/5 backdrop-blur-md rounded-lg p-6">
          <h3 className="text-2xl font-semibold mb-4">Emotional Analysis</h3>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={emotionsData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {emotionsData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {emotionsData.map((emotion, index) => (
              <div key={emotion.name} className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="text-sm">{emotion.name}: {emotion.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Transcript */}
      <div className="bg-white/5 backdrop-blur-md rounded-lg p-6">
        <h3 className="text-2xl font-semibold mb-4">Transcript</h3>
        <p className="text-gray-300 whitespace-pre-line">{transcript}</p>
      </div>
    </div>
  );
}

function ConsensusSection({ consensusData, finalScores }: { consensusData: string, finalScores: Score }) {
  const sections = consensusData.split('##').filter(Boolean);
  const scoreData = Object.entries(finalScores).map(([key, value]) => ({
    name: key.replace(/([A-Z])/g, ' $1').trim(),
    value: value
  }));
  
  return (
    <div className="space-y-8">
      {/* Consensus Scores Visualization */}
      <div className="bg-white/5 backdrop-blur-md rounded-lg p-6">
        <h3 className="text-2xl font-semibold mb-6">Consensus Scores</h3>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={scoreData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#444" />
              <XAxis dataKey="name" stroke="#fff" />
              <YAxis stroke="#fff" domain={[0, 10]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
              />
              <Bar dataKey="value" fill="#8884d8">
                {scoreData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={`hsl(${index * 50}, 70%, 60%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Discussion Points */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {sections.map((section) => {
          const [title, content] = section.split(':').map(s => s.trim());
          return (
            <div key={title} className="bg-white/5 backdrop-blur-md rounded-lg p-6">
              <h4 className="text-xl font-medium text-purple-300 mb-3 capitalize">
                {title.replace('Discussion Summary', '')}
              </h4>
              <p className="text-gray-300 leading-relaxed">{content}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function FeedbackPage() {
  const hi = [
    {
      logo: '/images/rbc.png',
    expandedImage: '/images/rbcc.png',
    },
    {
      logo: '/images/google.png',
      expandedImage: '/images/google2.webp',
    },
    {
      logo: '/images/password.png',
      expandedImage: '/images/passwordd.png',
    }

  ]

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

          {/* Analysis Section */}
          <section className="mb-12">
            <h2 className="text-3xl font-semibold mb-6">Analysis Results</h2>
            <AnalysisSection analysisData={analysisData} />
          </section>

         
            
            {/* Updated Consensus Section */}
            <div className="mb-12">
              <h2 className="text-3xl font-semibold mb-6">Judges Consensus</h2>
              <ConsensusSection 
                consensusData={analysisData?.evaluation_response.evaluation_results.main_evaluation.consensus_evaluation.discussion_summary || ''}
                finalScores={analysisData?.evaluation_response.evaluation_results.main_evaluation.consensus_evaluation.final_scores || {}}
              />
            </div>
          </div>

          {/* Company Feedback Cards */}
          <h2 className="text-3xl font-semibold mb-6">Detailed Company Feedback</h2>
          <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
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