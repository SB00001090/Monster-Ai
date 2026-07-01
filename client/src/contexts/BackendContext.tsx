import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMonsterApiBase, monsterApi, setMonsterApiBase } from "@/lib/monsterApi";

type BackendState = {
  apiBase: string;
  setApiBase: (url: string) => void;
  online: boolean | null;
  version: string | null;
  refresh: () => Promise<void>;
};

const BackendContext = createContext<BackendState | null>(null);

export function BackendProvider({ children }: { children: ReactNode }) {
  const [apiBase, setApiBaseState] = useState(getMonsterApiBase);
  const [online, setOnline] = useState<boolean | null>(null);
  const [version, setVersion] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const h = await monsterApi.health();
      setOnline(h.status === "ok");
      setVersion(h.version);
    } catch {
      setOnline(false);
      setVersion(null);
    }
  }, []);

  const setApiBase = useCallback(
    (url: string) => {
      setMonsterApiBase(url);
      setApiBaseState(getMonsterApiBase());
    },
    [],
  );

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh, apiBase]);

  const value = useMemo(
    () => ({ apiBase, setApiBase, online, version, refresh }),
    [apiBase, setApiBase, online, version, refresh],
  );

  return (
    <BackendContext.Provider value={value}>{children}</BackendContext.Provider>
  );
}

export function useBackend() {
  const ctx = useContext(BackendContext);
  if (!ctx) throw new Error("useBackend requires BackendProvider");
  return ctx;
}