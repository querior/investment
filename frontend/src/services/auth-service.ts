import { api } from './api';

export type LoginResponse = { access_token: string; token_type: string };

export const loginApi = async (email: string, password: string): Promise<LoginResponse> => {
  const res = await api.post('/auth/login', { email, password });
  return res.data;
};
