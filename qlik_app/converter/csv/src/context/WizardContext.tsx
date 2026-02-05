// src/context/WizardContext.tsx
import { createContext, useContext, useState } from "react";

type WizardContextType = {
  step: number;
  setStep: (n: number) => void;
  selectedApp: any;
  setSelectedApp: (app: any) => void;
};

const WizardContext = createContext<WizardContextType>(null!);

export const WizardProvider = ({ children }: { children: React.ReactNode }) => {
  const [step, setStep] = useState(1);
  const [selectedApp, setSelectedApp] = useState(null);

  return (
    <WizardContext.Provider value={{ step, setStep, selectedApp, setSelectedApp }}>
      {children}
    </WizardContext.Provider>
  );
};

export const useWizard = () => useContext(WizardContext);
