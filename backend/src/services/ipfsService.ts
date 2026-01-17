import axios from "axios";
import FormData from "form-data";

/**
 * Upload JSON-serializable data to IPFS.
 * Used for:
 *  - Aggregated model metadata
 *  - Block descriptors
 *
 * NEVER used for gradients or secrets.
 * 
 * Supports both:
 *  - Local IPFS Desktop node (http://localhost:5001)
 *  - Pinata cloud service (https://api.pinata.cloud)
 */
export async function uploadJSONToIPFS(
  data: unknown,
  name?: string
): Promise<{ cid: string }> {
  const apiUrl = process.env.IPFS_API_URL;
  const useLocalIPFS = process.env.IPFS_USE_LOCAL === "true";

  if (!apiUrl) {
    throw new Error("IPFS_API_URL environment variable not configured");
  }

  // Use local IPFS Desktop node
  if (useLocalIPFS) {
    return uploadToLocalIPFS(data, name, apiUrl);
  }

  // Use Pinata cloud service
  const apiKey = process.env.IPFS_API_KEY;
  const apiSecret = process.env.IPFS_API_SECRET;

  if (!apiKey || !apiSecret) {
    throw new Error("IPFS_API_KEY and IPFS_API_SECRET required for Pinata");
  }

  const payload = {
    pinataContent: data,
    pinataMetadata: {
      name: name ?? "healchain-object"
    }
  };

  const response = await axios.post(apiUrl, payload, {
    headers: {
      "Content-Type": "application/json",
      pinata_api_key: apiKey,
      pinata_secret_api_key: apiSecret
    }
  });

  return {
    cid: response.data.IpfsHash
  };
}

/**
 * Upload to local IPFS Desktop node
 * Uses IPFS HTTP API /api/v0/add endpoint
 */
async function uploadToLocalIPFS(
  data: unknown,
  name: string | undefined,
  apiUrl: string
): Promise<{ cid: string }> {
  // Convert JSON to Buffer for IPFS
  const jsonString = JSON.stringify(data);
  const buffer = Buffer.from(jsonString, "utf-8");

  // Create FormData for IPFS add endpoint
  const formData = new FormData();
  formData.append("file", buffer, {
    filename: name ? `${name}.json` : "healchain-object.json",
    contentType: "application/json"
  });

  try {
    const response = await axios.post(
      `${apiUrl}/api/v0/add`,
      formData,
      {
        headers: {
          ...formData.getHeaders()
        },
        maxContentLength: Infinity,
        maxBodyLength: Infinity
      }
    );

    // IPFS returns Hash (CID) in response
    // Response format: {"Name":"filename.json","Hash":"Qm...","Size":"123"}
    const result = typeof response.data === "string" 
      ? JSON.parse(response.data) 
      : response.data;
    
    return {
      cid: result.Hash
    };
  } catch (error: any) {
    if (error.code === "ECONNREFUSED") {
      throw new Error(
        "Cannot connect to local IPFS node. Make sure IPFS Desktop is running on http://localhost:5001"
      );
    }
    throw new Error(`IPFS upload failed: ${error.message}`);
  }
}

/**
 * Fetch JSON content from IPFS using a gateway.
 * Read-only, optional utility.
 * 
 * Supports both:
 *  - Local IPFS Desktop gateway (http://localhost:8080)
 *  - Public gateways (Pinata, IPFS.io, etc.)
 */
export async function fetchJSONFromIPFS<T = any>(
  cid: string,
  gateway?: string
): Promise<T> {
  // Use configured gateway or default based on IPFS mode
  const useLocalIPFS = process.env.IPFS_USE_LOCAL === "true";
  const defaultGateway = useLocalIPFS
    ? process.env.IPFS_GATEWAY_URL || "http://localhost:8080"
    : process.env.IPFS_GATEWAY_URL || "https://gateway.pinata.cloud/ipfs";

  const url = `${gateway || defaultGateway}/${cid}`;
  
  try {
    const response = await axios.get(url);
    return response.data as T;
  } catch (error: any) {
    if (error.code === "ECONNREFUSED" && useLocalIPFS) {
      throw new Error(
        "Cannot connect to local IPFS gateway. Make sure IPFS Desktop is running."
      );
    }
    throw new Error(`IPFS fetch failed: ${error.message}`);
  }
}