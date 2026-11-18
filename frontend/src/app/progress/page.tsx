import { Metadata } from 'next';
import HomeClient from '../home-client';

export const metadata: Metadata = {
  title: 'SQLArena · Tiến độ học tập',
  description: 'Theo dõi tiến độ giải bài và lịch sử nộp truy vấn SQL trên PostgreSQL 17',
};

export default function ProgressPage() {
  return <HomeClient routeSection="progress" />;
}
