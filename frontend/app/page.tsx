"use client";
import { useState } from 'react';
import axios from 'axios';

const API_URL = "http://localhost:8000";

export default function Home() {
  const [title, setTitle] = useState("");
  const [publicUrl, setPublicUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCreateSurvey = async () => {
    if (!title) return alert("Please enter a title");
    setLoading(true);
    
    try {
      // 1. Create the Survey
      const surveyRes = await axios.post(`${API_URL}/api/surveys`, { title });
      const id = surveyRes.data.id;

      // 2. Add exactly 5 Yes/No questions
      const questions = [
        "Are you currently in a well-lit room?",
        "Are you using a desktop or laptop computer?",
        "Is your face clearly visible in the camera?",
        "Are you the only person in the room?",
        "Do you consent to this video survey recording?"
      ];

      for (let i = 0; i < questions.length; i++) {
        await axios.post(`${API_URL}/api/surveys/${id}/questions`, {
          question_text: questions[i],
          order: i + 1
        });
      }

      // 3. Publish the Survey
      const publishRes = await axios.post(`${API_URL}/api/surveys/${id}/publish`);
      setPublicUrl(publishRes.data.public_url);

    } catch (error) {
      console.error(error);
      alert("Error creating survey. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-6 text-black">
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-center text-gray-800">Admin Dashboard</h1>

        {!publicUrl ? (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-2">Survey Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-md p-3 mb-6 focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="e.g., Privacy Consent Survey"
            />
            <button
              onClick={handleCreateSurvey}
              disabled={loading}
              className="w-full bg-blue-600 text-white font-semibold py-3 rounded-md hover:bg-blue-700 transition disabled:bg-blue-400"
            >
              {loading ? "Creating..." : "Create & Publish Survey"}
            </button>
          </>
        ) : (
          <div className="bg-green-50 p-5 rounded-md border border-green-200 text-center">
            <h2 className="text-green-800 font-bold mb-2">Survey Published!</h2>
            <p className="text-sm text-gray-600 mb-4">Share this link with your users:</p>
            <a 
              href={publicUrl} 
              className="text-blue-600 underline font-medium break-all"
            >
              http://localhost:3000{publicUrl}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}