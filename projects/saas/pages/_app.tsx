import { ClerkProvider } from '@clerk/nextjs';
import type { AppProps } from 'next/app';
import '../app/globals.css';

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ClerkProvider {...pageProps}>
      <Component {...pageProps} />
    </ClerkProvider>
  );
}