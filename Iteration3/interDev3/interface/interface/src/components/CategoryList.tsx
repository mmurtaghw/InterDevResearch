import { Box, List, ListItem, Spinner, Text, VStack } from "@chakra-ui/react";
import React from "react";
import useCategories, { Category } from "../hooks/useCategories";

interface Props {
  onSelectCategory: (selectedCategory: Category | null) => void;
  selectedCategory?: string;
  categoryTypeToFetch?: string;
}

const CategoryList: React.FC<Props> = ({
  onSelectCategory,
  selectedCategory,
  categoryTypeToFetch,
}) => {
  const { data, isLoading, error } = useCategories(categoryTypeToFetch);

  const getIdentifier = (category: Category) => category.value ?? category.name;

  const handleCategoryClick = (category: Category) => {
    const identifier = getIdentifier(category);
    if (selectedCategory === identifier) {
      onSelectCategory(null);
    } else {
      onSelectCategory(category);
    }
  };

  if (error) {
    console.error(error);
    return <Text>There was an error loading the categories.</Text>;
  }

  if (isLoading) return <Spinner />;

  if (!data) return null;

  return (
    <VStack align="stretch" spacing={2}>
      <List spacing={1}>
        {data.map((category) => {
          const identifier = getIdentifier(category);
          return (
            <ListItem key={identifier} py="5px">
              <Box
                as="button"
                role="button"
                aria-pressed={selectedCategory === identifier}
                onClick={() => handleCategoryClick(category)}
                justifyContent="start"
                width="full"
                textAlign="left"
                padding={0.5}
                wordBreak="break-word"
                cursor="pointer"
                _hover={{ color: "blue.500" }}
                backgroundColor={
                  selectedCategory === identifier ? "blue.100" : "transparent"
                }
                color={
                  selectedCategory === identifier ? "blue.700" : "inherit"
                }
                borderRadius="lg"
              >
                {category.name}
              </Box>
            </ListItem>
          );
        })}
      </List>
    </VStack>
  );
};

export default CategoryList;
