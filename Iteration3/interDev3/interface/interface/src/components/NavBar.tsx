import React, { useEffect, useState } from "react";
import { Box, Button, HStack, Image, Input, InputGroup, InputRightElement } from "@chakra-ui/react";
import { Link, useLocation } from "react-router-dom";
import logo from "../assets/logo.webp";

// Define an interface for the NavBar props
interface NavBarProps {
  searchQuery: string;
  onSearchSubmit: (query: string) => void;
  onLogout: () => void;
}

const NavBar: React.FC<NavBarProps> = ({
  searchQuery,
  onSearchSubmit,
  onLogout,
}) => {
  const location = useLocation();
  const [showLogout, setShowLogout] = useState(false);
  const [inputValue, setInputValue] = useState<string>(searchQuery);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setShowLogout((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!showLogout) return;
    const timeout = window.setTimeout(() => setShowLogout(false), 4000);
    return () => window.clearTimeout(timeout);
  }, [showLogout]);

  useEffect(() => {
    setInputValue(searchQuery);
  }, [searchQuery]);

  const linkStyle = (path: string) => ({
    variant: location.pathname === path ? "solid" : "ghost",
    colorScheme: "blue",
  });

  return (
    <HStack
      spacing={4}
      padding="10px"
      alignItems="center"
      flexWrap="wrap"
    >
      <Box position="relative" boxSize="60px">
        <Image src={logo} boxSize="60px" />
        {showLogout && (
          <Button
            size="xs"
            position="absolute"
            bottom={1}
            right={1}
            colorScheme="red"
            onClick={() => {
              onLogout();
              setShowLogout(false);
            }}
          >
            Log out
          </Button>
        )}
      </Box>
      <Button as={Link} to="/" {...linkStyle("/")}>
        Evidence View
      </Button>
      <Button as={Link} to="/collections" {...linkStyle("/collections")}>
        Collection View
      </Button>
      <Button as={Link} to="/submission" {...linkStyle("/submission")}>
        Submission View
      </Button>
      <InputGroup maxW="360px" flexGrow={1}>
        <Input
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onSearchSubmit(inputValue);
            }
          }}
          placeholder="Search trials"
        />
        <InputRightElement width="5rem">
          <Button
            h="1.75rem"
            size="sm"
            colorScheme="blue"
            onClick={() => onSearchSubmit(inputValue)}
          >
            Search
          </Button>
        </InputRightElement>
      </InputGroup>
    </HStack>
  );
};

export default NavBar;
