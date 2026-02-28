import React from "react";
import { Button, HStack, Image } from "@chakra-ui/react";
import { Link, useLocation } from "react-router-dom";
import ColorModeSwitch from "./ColorModeSwitch";
import logo from "../assets/logo.webp";

// Define an interface for the NavBar props
interface NavBarProps {
  resetSelectedFilter: () => void; // Function type specified
}

const NavBar: React.FC<NavBarProps> = ({ resetSelectedFilter }) => {
  const location = useLocation();

  const linkStyle = (path: string) => ({
    onClick: () => {
      if (location.pathname !== path) {
        resetSelectedFilter(); // Call the passed function
      }
    },
    variant: location.pathname === path ? "solid" : "ghost",
    colorScheme: "blue",
  });

  return (
    <HStack justifyContent="space-between" padding="10px">
      <Image src={logo} boxSize="60px" />
      <Button as={Link} to="/" {...linkStyle("/")}>
        Evidence View
      </Button>
      <Button as={Link} to="/collection" {...linkStyle("/collection")}>
        Collection View
      </Button>
      <Button as={Link} to="/submission" {...linkStyle("/submission")}>
        Submission View
      </Button>
      <ColorModeSwitch />
    </HStack>
  );
};

export default NavBar;
