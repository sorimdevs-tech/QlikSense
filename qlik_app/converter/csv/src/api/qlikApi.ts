

import axios from "axios";
 
// Use environment variable for production (set by Render), fallback to localhost for dev
// const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const BASE_URL = import.meta.env.VITE_API_URL || "https://qlik-sense-cloud.onrender.com";
 
// Convert FastAPI response → simple format
// ✅ UPDATE HERE
const mapApps = (data: any[]) =>
  data.map((a: any) => ({
    id: a.attributes?.id,
    name: a.attributes?.name,
    lastModifiedDate:
      a.attributes?.modifiedDate || a.attributes?.lastReloadTime,
  }));
// login test user 

export const testBrowserLogin = async (tenantUrl: string) => {
  const res = await axios.get(`${BASE_URL}`, {
    params: {
      tenant_url: tenantUrl,
    },
  });
  return res.data;
};


export const validateLogin = async (
  tenantUrl: string,
  connectAsUser: boolean,
  username: string,
  password: string
) => {
  const res = await axios.post(`${BASE_URL}/validate-login`, {
    tenant_url: tenantUrl,
    connect_as_user: connectAsUser,
    username,
    password,
  });

  return res.data;
};




// export const fetchApps = async () => {
//   const res = await axios.get(`${BASE_URL}/applications`);
//   return mapApps(res.data);
// };

export const fetchApps = async (tenantUrl: string) => {
  const res = await axios.get(`${BASE_URL}/applications`, {
    params: {
      tenant_url: tenantUrl,
    },
  });

  return mapApps(res.data);
};

export const fetchTables = async (appId: string, tenantUrl?: string) => {
  const params: any = {};
  if (tenantUrl) {
    params.tenant_url = tenantUrl;
  }
  
  try {
    const res = await axios.get(`${BASE_URL}/applications/${appId}/tables`, { params });
    return res.data.tables || [];
  } catch (error: any) {
    // Suppress 500 errors - tables may not be available for some apps
    if (error.response?.status === 500) {
      return [];
    }
    throw error;
  }
};

 
export const fetchTableData = async (appId: string, table_Name: string) => {
  console.log("🔍 Fetching table data from API...");
  console.log("URL:", `${BASE_URL}/applications/${appId}/script/${table_Name}/data`);
 
  const res = await axios.get(
   
    `${BASE_URL}/applications/${appId}/script/table/${table_Name}`
  );
 
  console.log("📦 Raw API Response:", res.data);
  console.log("📊 Response Type:", typeof res.data);
  console.log("📊 Response Keys:", Object.keys(res.data));
 
  // Handle different response formats
  if (res.data.success === false) {
    console.error("❌ API returned error:", res.data.error);
    console.error("Full error response:", res.data.full_error_response);
    throw new Error(res.data.error || "Failed to fetch data");
  }
 
  // Check for rows in response
  if (res.data.rows) {
    console.log("✅ Found rows in response:", res.data.rows.length);
    console.log("Sample row:", res.data.rows[0]);
    return res.data.rows;
  }
 
  // If the entire response is an array
  if (Array.isArray(res.data)) {
    console.log("✅ Response is array:", res.data.length);
    return res.data;
  }
 
  // Fallback
  console.warn("⚠️ Unexpected response format, returning empty array");
  return [];
};
 
// Temporary AI summary using table meta
export const fetchAISummary = async (appId: string) => {
  const tables = await fetchTables(appId);
 
  let text = `App contains ${tables.length} tables\n\n`;
 
  tables.forEach((t: any) => {
    text += `• ${t.name} (${t.fields?.length || 0} fields)\n`;
  });
 
  return text;
};
// qlikApi.ts
export const fetchVehicleSummary = async (appId: string, tableName: string) => {

  const url = `${BASE_URL}/vehicle-summary`;

  const res = await axios.get(url, {
    params: {
      app_id: appId,
      table_name: tableName,
    },
  });

  return res.data.summary;
};


 
export const connectQlik = async () => {
  try {
    const res = await axios.get(`${BASE_URL}/health`);
    return res.data;
  } catch (err) {
    throw new Error("Cannot connect to FastAPI backend");
  }
};