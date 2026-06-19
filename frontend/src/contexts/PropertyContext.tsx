/* eslint-disable react-refresh/only-export-components */
import {
  useCallback,
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  createProperty,
  fetchProperties,
  type Property,
} from "@/api/properties";

const ACTIVE_PROPERTY_STORAGE_KEY = "geo_engine_active_property_id";

type PropertyContextValue = {
  activeProperty: Property | null;
  properties: Property[];
  loading: boolean;
  setActiveProperty: (property: Property) => void;
  addProperty: (
    property: Pick<Property, "name" | "domain" | "brand_name">,
  ) => Promise<Property>;
};

const PropertyContext = createContext<PropertyContextValue | null>(null);

export function PropertyProvider({ children }: { children: ReactNode }) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [activeProperty, setActivePropertyState] = useState<Property | null>(
    null,
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadProperties() {
      try {
        const propertyList = await fetchProperties();

        if (!isMounted) {
          return;
        }

        setProperties(propertyList);

        const storedPropertyId = Number(
          localStorage.getItem(ACTIVE_PROPERTY_STORAGE_KEY),
        );

        const selectedProperty =
          propertyList.find((property) => property.id === storedPropertyId) ||
          propertyList[0] ||
          null;

        setActivePropertyState(selectedProperty);

        if (selectedProperty) {
          localStorage.setItem(
            ACTIVE_PROPERTY_STORAGE_KEY,
            String(selectedProperty.id),
          );
        }
      } catch (error) {
        console.error(error);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadProperties();

    return () => {
      isMounted = false;
    };
  }, []);

  const setActiveProperty = useCallback((property: Property) => {
    setActivePropertyState(property);
    localStorage.setItem(ACTIVE_PROPERTY_STORAGE_KEY, String(property.id));
  }, []);

  const addProperty = useCallback(async (
    property: Pick<Property, "name" | "domain" | "brand_name">,
  ) => {
    const createdProperty = await createProperty(property);

    setProperties((currentProperties) => [
      ...currentProperties,
      createdProperty,
    ]);
    setActiveProperty(createdProperty);

    return createdProperty;
  }, [setActiveProperty]);

  const value = useMemo<PropertyContextValue>(
    () => ({
      activeProperty,
      properties,
      loading,
      setActiveProperty,
      addProperty,
    }),
    [activeProperty, addProperty, properties, loading, setActiveProperty],
  );

  return (
    <PropertyContext.Provider value={value}>
      {children}
    </PropertyContext.Provider>
  );
}

export function useProperty() {
  const context = useContext(PropertyContext);

  if (!context) {
    throw new Error("useProperty must be used within PropertyProvider");
  }

  return context;
}
