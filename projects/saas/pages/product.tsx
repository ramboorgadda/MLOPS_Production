"use client"

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { useAuth } from '@clerk/nextjs';
import { UserButton } from '@clerk/nextjs';

function IdeaGenerator() {
    const { getToken, isLoaded, isSignedIn } = useAuth();
    const [idea, setIdea] = useState<string>('…loading');

    useEffect(() => {
        if (!isLoaded) {
            return;
        }

        if (!isSignedIn) {
            setIdea('Authentication required');
            return;
        }

        let buffer = '';
        let isCancelled = false;
        const controller = new AbortController();
        const decoder = new TextDecoder();

        (async () => {
            const jwt = await getToken();
            if (!jwt) {
                setIdea('Authentication required');
                return;
            }

            setIdea('');

            const response = await fetch('/api', {
                signal: controller.signal,
                headers: { Authorization: `Bearer ${jwt}` },
            });

            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }

            if (!response.body) {
                throw new Error('Streaming response body is missing');
            }

            const reader = response.body.getReader();

            while (!isCancelled) {
                const { done, value } = await reader.read();
                if (done) {
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                setIdea(buffer);
            }
        })().catch((err: unknown) => {
            if (controller.signal.aborted || isCancelled) {
                return;
            }

            console.error('Stream error:', err);
            setIdea('Could not generate an idea. Check the browser console and API logs.');
        });

        return () => {
            isCancelled = true;
            controller.abort();
        };
    }, [getToken, isLoaded, isSignedIn]);

    return (
        <div className="container mx-auto px-4 py-12">
            <header className="text-center mb-12">
                <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-4">
                    Business Idea Generator
                </h1>
                <p className="text-gray-600 dark:text-gray-400 text-lg">
                    AI-powered innovation at your fingertips
                </p>
            </header>

            <div className="max-w-3xl mx-auto">
                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 backdrop-blur-lg bg-opacity-95">
                    {idea === '…loading' ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-pulse text-gray-400">
                                Generating your business idea...
                            </div>
                        </div>
                    ) : idea === '' ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-pulse text-gray-400">
                                Receiving response...
                            </div>
                        </div>
                    ) : (
                        <div className="markdown-content text-gray-700 dark:text-gray-300">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm, remarkBreaks]}
                            >
                                {idea}
                            </ReactMarkdown>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function Product() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
            <div className="absolute top-4 right-4">
                <UserButton showName={true} />
            </div>

            <IdeaGenerator />
        </main>
    );
}
