import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Box,
} from "@chakra-ui/react";
import CategoryList from "./CategoryList";
import { Category } from "../hooks/useCategories";

interface Props {
  onSelectCategory: (selectedCategory: Category | null) => void;
  categoryName: string;
  selectedCategory?: string;
  categoryTypeToFetch?: string;
}

const CategoryHolder = ({
  onSelectCategory,
  categoryName,
  selectedCategory,
  categoryTypeToFetch,
}: Props) => {
  return (
    <Accordion allowToggle>
      <AccordionItem>
        <h2>
          <AccordionButton>
            <Box as="span" flex="1" textAlign="left">
              {categoryName}
            </Box>
            <AccordionIcon />
          </AccordionButton>
        </h2>
        <AccordionPanel pb={4}>
          <CategoryList
            onSelectCategory={onSelectCategory}
            selectedCategory={selectedCategory}
            categoryTypeToFetch={categoryTypeToFetch}
          ></CategoryList>
        </AccordionPanel>
      </AccordionItem>
    </Accordion>
  );
};

export default CategoryHolder;
