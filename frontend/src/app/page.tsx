import { Metadata } from 'next';
import HomeClient from './home-client';

export const metadata: Metadata = {
  title: 'SQLArena · Thực hành SQL PostgreSQL 17',
  description: 'Hệ thống thực hành, kiểm định kép và chấm điểm truy vấn SQL tự động trên PostgreSQL 17',
};

export default function HomePage() {
  return <HomeClient routeSection="workbench" />;
}
