import {
  Box,
  Button,
  HStack,
  List,
  ListItem,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import React from "react";
import useCategories, { Category } from "../hooks/useCategories";

interface Props {
  onSelectCategory: (selectedCategory: Category | null) => void;
  selectedCategory?: string;
  categoryTypeToFetch?: string;
}

const CategoryList = ({
  onSelectCategory,
  selectedCategory,
  categoryTypeToFetch,
}: Props) => {
  const { data, isLoading, error } = useCategories(categoryTypeToFetch);

  const handleCategoryClick = (category: Category) => {
    // Check if the clicked category is the same as the selected one
    if (selectedCategory === category.name) {
      onSelectCategory(null);
    } else {
      onSelectCategory(category);
    }
  };

  if (error) return <Text>There was an error loading the categories.</Text>;
  if (isLoading) return <Spinner />;

  return (
    <VStack align="stretch" spacing={2}>
      <List spacing={1}>
        {data.map((category) => (
          <ListItem key={category.code || category.name} py="5px">
            <Box
              as="button"
              onClick={() => handleCategoryClick(category)}
              justifyContent="start"
              width="full"
              textAlign="left"
              padding={0.5}
              wordBreak="break-word"
              cursor="pointer"
              _hover={{ color: "blue.500" }}
              backgroundColor={
                selectedCategory === category.name ? "blue.100" : "transparent"
              }
              color={
                selectedCategory === category.name ? "blue.700" : "inherit"
              }
              borderRadius="lg" // Adjusted for more rounded edges
            >
              {category.name}
            </Box>
          </ListItem>
        ))}
      </List>
    </VStack>
  );
};

export default CategoryList;
