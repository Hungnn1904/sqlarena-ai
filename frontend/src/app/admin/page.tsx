import { Metadata } from 'next';
import HomeClient from '../home-client';

export const metadata: Metadata = {
  title: 'SQLArena · Quản trị hệ thống',
  description: 'Quản trị người dùng, sinh đề AI, duyệt đề và ngân hàng câu hỏi SQL PostgreSQL 17',
};

export default function AdminPage() {
  return <HomeClient routeSection="admin" />;
}
