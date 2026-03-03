import { error } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';
import type { PageServerLoad } from './$types';

type SettingField = { value: unknown; env_override: boolean };

export type SettingsData = {
  media_data_location: SettingField;
  prefer_extended: SettingField;
  qbt_hostname: SettingField;
  qbt_username: SettingField;
  qbt_password: SettingField;
  qbt_path_mapping: SettingField;
  qbt_category: SettingField;
  qbt_download_location: SettingField;
  qbt_polling_rate: SettingField;
  log_level: SettingField;
};

export const load: PageServerLoad = async ({ fetch }) => {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/settings`);
  if (!res.ok) error(res.status, 'Failed to load settings');
  const settings: SettingsData = await res.json();
  return { settings };
};
