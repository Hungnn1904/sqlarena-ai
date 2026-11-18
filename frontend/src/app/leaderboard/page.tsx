import { Metadata } from 'next';
import HomeClient from '../home-client';

export const metadata: Metadata = {
  title: 'SQLArena · Bảng xếp hạng',
  description: 'Bảng xếp hạng giải bài SQL tuần và tháng trên PostgreSQL 17',
};

export default function LeaderboardPage() {
  return <HomeClient routeSection="leaderboard" />;
}
