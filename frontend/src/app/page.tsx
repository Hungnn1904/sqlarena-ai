import { Metadata } from 'next';
import HomeClient from './home-client';

export const metadata: Metadata = {
  title: 'SQLArena AI Question Generator',
  description: '7-step AI pipeline for SQL question generation',
};

export default function Home() {
  return <HomeClient />;
}
