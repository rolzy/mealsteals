import { createContext, useContext } from "react";
import DealAPIClient from "../DealAPIClient";

const ApiContext = createContext();

export default function ApiProvider({ children }) {
  const api = new DealAPIClient();
  return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>;
}

export function useApi() {
  return useContext(ApiContext);
}
