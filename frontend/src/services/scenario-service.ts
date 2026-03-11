import { api } from './api';

export type ScenarioDto = {
  id: number;
  name: string;
  description: string;
  config_json: string;
  owner_email: string;
};

export const listScenariosApi = async (): Promise<ScenarioDto[]> => {
  const res = await api.get('/scenarios');
  return res.data;
};
