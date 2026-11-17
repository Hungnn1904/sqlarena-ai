import { Metadata } from 'next';
import HomeClient from '../home-client';

export const metadata: Metadata = {
  title: 'SQLArena · Quản trị',
  description: 'Cổng quản trị người dùng, sinh đề AI và ngân hàng câu hỏi PostgreSQL 17',
};

export default function AdminPage() {
  return <HomeClient forceSurface="admin" />;
}
