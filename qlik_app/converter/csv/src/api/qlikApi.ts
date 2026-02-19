

// import axios from "axios";
 
// // Use environment variable for production (set by Render), fallback to localhost for dev
// const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
// // const BASE_URL = import.meta.env.VITE_API_URL || "https://qlik-sense-cloud.onrender.com";
 
// // Convert FastAPI response → simple format
// // ✅ UPDATE HERE
// const mapApps = (data: any[]) =>
//   data.map((a: any) => ({
//     id: a.attributes?.id,
//     name: a.attributes?.name,
//     lastModifiedDate:
//       a.attributes?.modifiedDate || a.attributes?.lastReloadTime,
//   }));
// // login test user 

// export const testBrowserLogin = async (tenantUrl: string) => {
//   const res = await axios.get(`${BASE_URL}`, {
//     params: {
//       tenant_url: tenantUrl,
//     },
//   });
//   return res.data;
// };


// export const validateLogin = async (
//   tenantUrl: string,
//   connectAsUser: boolean,
//   username: string,
//   password: string
// ) => {
//   const res = await axios.post(`${BASE_URL}/validate-login`, {
//     tenant_url: tenantUrl,
//     connect_as_user: connectAsUser,
//     username,
//     password,
//   });

//   return res.data;
// };




// // export const fetchApps = async () => {
// //   const res = await axios.get(`${BASE_URL}/applications`);
// //   return mapApps(res.data);
// // };

// export const fetchApps = async (tenantUrl: string) => {
//   const params: any = {};
//   if (tenantUrl) {
//     params.tenant_url = tenantUrl;
//   }
  
//   const res = await axios.get(`${BASE_URL}/applications`, { params });

//   return mapApps(res.data);
// };

// export const fetchTables = async (appId: string, tenantUrl?: string) => {
//   const params: any = {};
//   if (tenantUrl) {
//     params.tenant_url = tenantUrl;
//   }
  
//   try {
//     const res = await axios.get(`${BASE_URL}/applications/${appId}/tables`, { params });
//     return res.data.tables || [];
//   } catch (error: any) {
//     // Suppress 500 errors - tables may not be available for some apps
//     if (error.response?.status === 500) {
//       return [];
//     }
//     throw error;
//   }
// };

 
// // 
// export const fetchTableData = async (appId: string, table_Name: string) => {
//   console.log("🔍 Fetching table data from API...");
//   console.log("📍 Table Name:", table_Name);
  
//   try {
//     // First try: Use the enhanced table data endpoint (works for CSV loaded files with intelligent name matching)
//     const enhancedUrl = `${BASE_URL}/applications/${appId}/table/${table_Name}/data/enhanced`;
//     console.log("URL (attempt 1 - enhanced):", enhancedUrl);
    
//     const res = await axios.get(enhancedUrl);
    
//     console.log("📦 Raw API Response:", res.data);
//     console.log("📊 Response Type:", typeof res.data);
    
//     // Handle different response formats
//     if (res.data.success === false) {
//       console.error("❌ API returned error:", res.data.error);
//       throw new Error(res.data.error || "Failed to fetch data");
//     }
    
//     // Check for rows in response
//     if (res.data.rows) {
//       console.log("✅ Found rows in response:", res.data.rows.length);
//       console.log("Sample row:", res.data.rows[0]);
//       return res.data.rows;
//     }
    
//     // If the entire response is an array
//     if (Array.isArray(res.data)) {
//       console.log("✅ Response is array:", res.data.length);
//       return res.data;
//     }
    
//     console.warn("⚠️ Unexpected response format from enhanced endpoint");
//     throw new Error("Unexpected response format");
    
//   } catch (primaryError: any) {
//     console.log("⚠️ Enhanced endpoint failed, trying standard table data endpoint...");
    
//     try {
//       // Second try: Use the standard table data endpoint
//       const tableDataUrl = `${BASE_URL}/applications/${appId}/table/${table_Name}/data`;
//       console.log("URL (attempt 2 - standard):", tableDataUrl);
      
//       const res = await axios.get(tableDataUrl);
      
//       console.log("✅ Got data from standard table endpoint");
      
//       // Handle different response formats
//       if (res.data.success === false) {
//         throw new Error(res.data.error || "Failed to fetch data");
//       }
      
//       if (res.data.rows) {
//         return res.data.rows;
//       }
      
//       if (Array.isArray(res.data)) {
//         return res.data;
//       }
      
//       throw new Error("Unexpected response format");
      
//     } catch (secondaryError: any) {
//       console.log("⚠️ Standard endpoint failed, trying script table endpoint...");
      
//       try {
//         // Third try: Use the script table endpoint (for INLINE data)
//         const scriptUrl = `${BASE_URL}/applications/${appId}/script/table/${table_Name}`;
//         console.log("URL (attempt 3 - script):", scriptUrl);
        
//         const res = await axios.get(scriptUrl);
        
//         console.log("✅ Got data from script endpoint");
        
//         // Handle different response formats
//         if (res.data.success === false) {
//           throw new Error(res.data.error || "Failed to fetch script table data");
//         }
        
//         if (res.data.rows) {
//           return res.data.rows;
//         }
        
//         if (Array.isArray(res.data)) {
//           return res.data;
//         }
        
//         return [];
        
//       } catch (tertiaryError: any) {
//         console.error("❌ All endpoints failed");
//         console.error("Enhanced error:", primaryError.response?.data || primaryError.message);
//         console.error("Standard error:", secondaryError.response?.data || secondaryError.message);
//         console.error("Script error:", tertiaryError.response?.data || tertiaryError.message);
        
//         const errorMessage = 
//           primaryError.response?.data?.detail || 
//           secondaryError.response?.data?.detail ||
//           tertiaryError.response?.data?.detail ||
//           primaryError.message ||
//           "Could not fetch table data";
        
//         throw new Error(
//           `Could not fetch table "${table_Name}". Error: ${errorMessage}`
//         );
//       }
//     }
//   }
// };
 
// // Temporary AI summary using table meta
// export const fetchAISummary = async (appId: string) => {
//   const tables = await fetchTables(appId);
 
//   let text = `App contains ${tables.length} tables\n\n`;
 
//   tables.forEach((t: any) => {
//     text += `• ${t.name} (${t.fields?.length || 0} fields)\n`;
//   });
 
//   return text;
// };
// // qlikApi.ts
// export const fetchVehicleSummary = async (appId: string, tableName: string) => {
//   const url = `${BASE_URL}/vehicle-summary`;

//   try {
//     const res = await axios.get(url, {
//       params: {
//         app_id: appId,
//         table_name: tableName,
//       },
//     });

//     return res.data.summary;
//   } catch (e) {
//     console.warn("⚠️ Backend summary generation failed, continuing without summary");
//     return null;
//   }
// };

// // Generate summary from table data locally (frontend)
// // This avoids backend dependency and works with any data format
// export const generateSummaryFromData = (rows: any[], tableName: string): any => {
//   if (!rows || rows.length === 0) {
//     return { table: tableName, totalRows: 0 };
//   }

//   const summary: any = {
//     table: tableName,
//     totalRows: rows.length,
//     columns: Object.keys(rows[0]),
//     columnCount: Object.keys(rows[0]).length,
//     numericAnalysis: {},
//     categoryCounts: {},
//   };

//   // Analyze each column
//   const firstRow = rows[0];
  
//   for (const key in firstRow) {
//     const values: number[] = [];
//     const textValues: Set<string> = new Set();

//     rows.forEach((row: any) => {
//       const val = row[key];
      
//       // Skip placeholder values
//       if (val && typeof val === "string" && val.includes("not accessible")) {
//         return;
//       }

//       // Try to parse as number
//       if (val !== null && val !== undefined && val !== "") {
//         const strVal = String(val).replace(/,/g, "").trim();
        
//         if (!isNaN(Number(strVal)) && strVal !== "") {
//           values.push(Number(strVal));
//         } else {
//           textValues.add(strVal);
//         }
//       }
//     });

//     // Numeric analysis
//     if (values.length > 0) {
//       summary.numericAnalysis[key] = {
//         min: Math.min(...values),
//         max: Math.max(...values),
//         avg: Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 100) / 100,
//         count: values.length,
//       };
//     }

//     // Category analysis (for low cardinality columns)
//     if (textValues.size > 0 && textValues.size <= 20) {
//       const counts: any = {};
      
//       rows.forEach((row: any) => {
//         const val = String(row[key]);
//         if (!val.includes("not accessible")) {
//           counts[val] = (counts[val] || 0) + 1;
//         }
//       });

//       // Sort by frequency and get top 5
//       const sorted = Object.entries(counts)
//         .sort((a: any, b: any) => b[1] - a[1])
//         .slice(0, 5);

//       if (sorted.length > 0) {
//         summary.categoryCounts[key] = Object.fromEntries(sorted);
//       }
//     }
//   }

//   return summary;
// };



 
// export const connectQlik = async () => {
//   try {
//     const res = await axios.get(`${BASE_URL}/health`);
//     return res.data;
//   } catch (err) {
//     throw new Error("Cannot connect to FastAPI backend");
//   }
// };

// // Get simple table data (just structure without complex hypercube)
// export const fetchTableDataSimple = async (appId: string, table_Name: string) => {
//   console.log("📊 Fetching simple table data (structure only)...");
//   console.log("📍 Table Name:", table_Name);
  
//   try {
//     const url = `${BASE_URL}/applications/${appId}/table/${table_Name}/data/simple`;
//     console.log("URL:", url);
    
//     const res = await axios.get(url);
    
//     if (res.data.success === false) {
//       throw new Error(res.data.error || "Failed to fetch table data");
//     }
    
//     return res.data;
//   } catch (e) {
//     console.error("❌ Error fetching simple table data:", e);
//     throw e;
//   }
// };

// // Export table as CSV
// export const exportTableAsCSV = async (appId: string, table_Name: string) => {
//   console.log("📥 Exporting table as CSV...");
//   console.log("📍 Table Name:", table_Name);
  
//   try {
//     const url = `${BASE_URL}/applications/${appId}/table/${table_Name}/export/csv`;
//     console.log("URL:", url);
    
//     const res = await axios.get(url, {
//       responseType: "text"
//     });
    
//     return res.data;
//   } catch (e) {
//     console.error("❌ Error exporting table as CSV:", e);
//     throw e;
//   }
// };

// // Download CSV file to user's computer
// export const downloadCSVFile = (csvContent: string, fileName: string) => {
//   const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
//   const link = document.createElement("a");
//   const url = URL.createObjectURL(blob);
  
//   link.setAttribute("href", url);
//   link.setAttribute("download", fileName);
//   link.style.visibility = "hidden";
  
//   document.body.appendChild(link);
//   link.click();
//   document.body.removeChild(link);
// };







import axios from "axios";

// Use environment variable for production (set by Render), fallback to localhost for dev
// const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const BASE_URL = import.meta.env.VITE_API_URL || "https://qliksense-xd7f.onrender.com";

// Convert FastAPI response → simple format
const mapApps = (data: any[]) =>
  data.map((a: any) => ({
    id: a.attributes?.id,
    name: a.attributes?.name,
    lastModifiedDate:
      a.attributes?.modifiedDate || a.attributes?.lastReloadTime,
  }));

// Test browser login
export const testBrowserLogin = async (tenantUrl: string) => {
  const res = await axios.get(`${BASE_URL}`, {
    params: { tenant_url: tenantUrl },
  });
  return res.data;
};

// Validate login
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

// Fetch apps
export const fetchApps = async (tenantUrl: string) => {
  const params: any = {};
  if (tenantUrl) {
    params.tenant_url = tenantUrl;
  }

  const res = await axios.get(`${BASE_URL}/applications`, { params });
  return mapApps(res.data);
};

// Fetch tables
export const fetchTables = async (appId: string, tenantUrl?: string) => {
  const params: any = {};
  if (tenantUrl) {
    params.tenant_url = tenantUrl;
  }

  try {
    const res = await axios.get(
      `${BASE_URL}/applications/${appId}/tables`,
      { params }
    );
    return res.data.tables || [];
  } catch (error: any) {
    if (error.response?.status === 500) {
      return [];
    }
    throw error;
  }
};

// ✅ CLEAN TABLE DATA (Only standard endpoint)
export const fetchTableData = async (
  appId: string,
  table_Name: string
) => {
  console.log("🔍 Fetching table data from API...");
  console.log("📍 Table Name:", table_Name);

  try {
    const url = `${BASE_URL}/applications/${appId}/table/${table_Name}/data`;
    console.log("URL:", url);

    const res = await axios.get(url);

    if (res.data.success === false) {
      throw new Error(res.data.error || "Failed to fetch data");
    }

    if (res.data.rows) {
      return res.data.rows;
    }

    if (Array.isArray(res.data)) {
      return res.data;
    }

    return [];
  } catch (error: any) {
    console.error(
      "❌ Failed to fetch table data:",
      error.response?.data || error.message
    );

    const errorMessage =
      error.response?.data?.detail ||
      error.message ||
      "Could not fetch table data";

    throw new Error(
      `Could not fetch table "${table_Name}". Error: ${errorMessage}`
    );
  }
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

// Backend vehicle summary
export const fetchVehicleSummary = async (
  appId: string,
  tableName: string
) => {
  const url = `${BASE_URL}/vehicle-summary`;

  try {
    const res = await axios.get(url, {
      params: {
        app_id: appId,
        table_name: tableName,
      },
    });

    return res.data.summary;
  } catch (e) {
    console.warn(
      "⚠️ Backend summary generation failed, continuing without summary"
    );
    return null;
  }
};

// Generate summary from table data locally
export const generateSummaryFromData = (
  rows: any[],
  tableName: string
): any => {
  if (!rows || rows.length === 0) {
    return { table: tableName, totalRows: 0 };
  }

  const summary: any = {
    table: tableName,
    totalRows: rows.length,
    columns: Object.keys(rows[0]),
    columnCount: Object.keys(rows[0]).length,
    numericAnalysis: {},
    categoryCounts: {},
  };

  const firstRow = rows[0];

  for (const key in firstRow) {
    const values: number[] = [];
    const textValues: Set<string> = new Set();

    rows.forEach((row: any) => {
      const val = row[key];

      if (
        val &&
        typeof val === "string" &&
        val.includes("not accessible")
      ) {
        return;
      }

      if (val !== null && val !== undefined && val !== "") {
        const strVal = String(val).replace(/,/g, "").trim();

        if (!isNaN(Number(strVal)) && strVal !== "") {
          values.push(Number(strVal));
        } else {
          textValues.add(strVal);
        }
      }
    });

    if (values.length > 0) {
      summary.numericAnalysis[key] = {
        min: Math.min(...values),
        max: Math.max(...values),
        avg:
          Math.round(
            (values.reduce((a, b) => a + b, 0) / values.length) * 100
          ) / 100,
        count: values.length,
      };
    }

    if (textValues.size > 0 && textValues.size <= 20) {
      const counts: any = {};

      rows.forEach((row: any) => {
        const val = String(row[key]);
        if (!val.includes("not accessible")) {
          counts[val] = (counts[val] || 0) + 1;
        }
      });

      const sorted = Object.entries(counts)
        .sort((a: any, b: any) => b[1] - a[1])
        .slice(0, 5);

      if (sorted.length > 0) {
        summary.categoryCounts[key] = Object.fromEntries(sorted);
      }
    }
  }

  return summary;
};

// Health check
export const connectQlik = async () => {
  try {
    const res = await axios.get(`${BASE_URL}/health`);
    return res.data;
  } catch (err) {
    throw new Error("Cannot connect to FastAPI backend");
  }
};

// Simple table structure endpoint
export const fetchTableDataSimple = async (
  appId: string,
  table_Name: string
) => {
  const url = `${BASE_URL}/applications/${appId}/table/${table_Name}/data/simple`;

  const res = await axios.get(url);

  if (res.data.success === false) {
    throw new Error(res.data.error || "Failed to fetch table data");
  }

  return res.data;
};

// Export CSV
export const exportTableAsCSV = async (
  appId: string,
  table_Name: string
) => {
  const url = `${BASE_URL}/applications/${appId}/table/${table_Name}/export/csv`;

  const res = await axios.get(url, {
    responseType: "text",
  });

  return res.data;
};

// Download CSV file
export const downloadCSVFile = (
  csvContent: string,
  fileName: string
) => {
  const blob = new Blob([csvContent], {
    type: "text/csv;charset=utf-8;",
  });

  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute("download", fileName);
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// 🤖 AI-powered summary using Hugging Face LLM
export const fetchAISummaryFromBackend = async (
  tableName: string,
  rows: any[],
  summary: any
): Promise<string[]> => {
  try {
    // Prepare metrics for AI
    const metrics: any = {
      "Total Records": rows.length,
      "Column Count": summary?.columnCount || Object.keys(rows[0] || {}).length,
    };

    // Add numeric analysis if available
    if (summary?.numericAnalysis) {
      for (const [key, value] of Object.entries(summary.numericAnalysis)) {
        const v = value as any;
        if (v.avg !== undefined) {
          metrics[`${key} Average`] = v.avg;
        }
        if (v.min !== undefined) {
          metrics[`${key} Min`] = v.min;
        }
        if (v.max !== undefined) {
          metrics[`${key} Max`] = v.max;
        }
      }
    }

    // Add category counts if available
    if (summary?.categoryCounts) {
      for (const [key, value] of Object.entries(summary.categoryCounts)) {
        metrics[`Top ${key}`] = value;
      }
    }

    // Calculate total value from numeric columns
    let totalValue = 0;
    rows.forEach((row) => {
      Object.values(row).forEach((val) => {
        const num = Number(val);
        if (!isNaN(num) && num > 100) {
          totalValue += num;
        }
      });
    });
    if (totalValue > 0) {
      metrics["Total Value"] = totalValue;
    }

    // Send actual sample data (first 10 rows) for better AI context
    const sampleData = rows.slice(0, 10);

    const res = await axios.post(`${BASE_URL}/ai/summary`, {
      table_name: tableName,
      metrics: metrics,
      row_count: rows.length,
      column_count: summary?.columnCount || Object.keys(rows[0] || {}).length,
      sample_data: sampleData,  // Send actual table rows for AI analysis
    });

    if (res.data.success && res.data.summary) {
      // Split summary into bullet points for display
      const summaryText = res.data.summary;
      
      // Check if AI returned bullet points (starts with •)
      if (summaryText.includes('•')) {
        // Split by bullet points
        const bullets = summaryText
          .split(/•/)
          .map((s: string) => s.trim())
          .filter((s: string) => s.length > 0);
        return bullets;
      }
      
      // If it's a paragraph, split by sentences and create bullets
      const sentences = summaryText.split(/[.!?]+/).filter((s: string) => s.trim());
      return sentences.map((s: string) => s.trim()).filter((s: string) => s.length > 0);
    }

    return [];
  } catch (error: any) {
    console.error("❌ AI Summary error:", error.response?.data || error.message);
    // Return empty array to fall back to local summary
    return [];
  }
};
