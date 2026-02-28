import React, { ReactNode } from "react";
import { Grid, useMediaQuery } from "@chakra-ui/react";
import { useLocation } from "react-router-dom";

interface GridLayoutProps {
  children: ReactNode; // This type allows any valid React children
}

const GridLayout: React.FC<GridLayoutProps> = ({ children }) => {
  const location = useLocation();
  const [isLargerThanLG] = useMediaQuery("(min-width: 62em)");
  const isTrialRoute = location.pathname.startsWith("/trial/");

  const templateAreas =
    isTrialRoute && isLargerThanLG
      ? { base: `"nav" "main"`, lg: `"nav" "main"` }
      : { base: `"nav" "main"`, lg: `"nav nav" "aside main"` };

  const templateColumns =
    isTrialRoute && isLargerThanLG
      ? { base: "1fr", lg: "1fr" }
      : { base: "1fr", lg: "200px 1fr" };

  return (
    <Grid
      templateAreas={templateAreas}
      templateColumns={templateColumns}
      height="100vh" // Adjust as needed
    >
      {children}
    </Grid>
  );
};

export default GridLayout;
