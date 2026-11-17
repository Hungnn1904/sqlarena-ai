import { Metadata } from 'next';
import HomeClient from './home-client';

export const metadata: Metadata = {
  title: 'SQLArena · Thực hành SQL PostgreSQL 17',
  description: 'Môi trường thực hành và chấm điểm truy vấn SQL tự động trên PostgreSQL 17',
};

export default function Home() {
  return <HomeClient />;
}
