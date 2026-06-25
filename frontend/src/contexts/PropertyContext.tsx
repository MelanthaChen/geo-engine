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
  updateProperty,
  type Property,
  type PropertyPayload,
} from "@/api/properties";

const ACTIVE_PROPERTY_STORAGE_KEY = "geo_engine_active_property_id";

type PropertyContextValue = {
  activeProperty: Property | null;
  activePropertyId: number | null;
  properties: Property[];
  loading: boolean;
  setActiveProperty: (property: Property) => void;
  addProperty: (property: PropertyPayload) => Promise<Property>;
  updateActiveProperty: (
    property: Partial<PropertyPayload>,
  ) => Promise<Property | null>;
  refreshProperties: () => Promise<Property[]>;
};

const PropertyContext = createContext<PropertyContextValue | null>(null);

export function PropertyProvider({ children }: { children: ReactNode }) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [activeProperty, setActivePropertyState] = useState<Property | null>(
    null,
  );
  const [loading, setLoading] = useState(true);

  const selectFromProperties = useCallback((propertyList: Property[]) => {
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

    return selectedProperty;
  }, []);

  const refreshProperties = useCallback(async () => {
    const propertyList = await fetchProperties();

    setProperties(propertyList);
    selectFromProperties(propertyList);

    return propertyList;
  }, [selectFromProperties]);

  useEffect(() => {
    let isMounted = true;

    async function loadProperties() {
      try {
        const propertyList = await fetchProperties();

        if (!isMounted) {
          return;
        }

        setProperties(propertyList);
        selectFromProperties(propertyList);
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
  }, [selectFromProperties]);

  const setActiveProperty = useCallback((property: Property) => {
    setActivePropertyState(property);
    localStorage.setItem(ACTIVE_PROPERTY_STORAGE_KEY, String(property.id));
  }, []);

  const addProperty = useCallback(async (property: PropertyPayload) => {
    const createdProperty = await createProperty(property);
    localStorage.setItem(
      ACTIVE_PROPERTY_STORAGE_KEY,
      String(createdProperty.id),
    );

    const propertyList = await fetchProperties();
    const selectedProperty =
      propertyList.find(
        (currentProperty) => currentProperty.id === createdProperty.id,
      ) || createdProperty;

    setProperties(propertyList);
    setActivePropertyState(selectedProperty);

    return selectedProperty;
  }, []);

  const updateActiveProperty = useCallback(async (
    property: Partial<PropertyPayload>,
  ) => {
    if (!activeProperty) {
      return null;
    }

    const updatedProperty = await updateProperty(activeProperty.id, property);

    setProperties((currentProperties) =>
      currentProperties.map((currentProperty) =>
        currentProperty.id === updatedProperty.id
          ? updatedProperty
          : currentProperty,
      ),
    );
    setActiveProperty(updatedProperty);

    return updatedProperty;
  }, [activeProperty, setActiveProperty]);

  const value = useMemo<PropertyContextValue>(
    () => ({
      activeProperty,
      activePropertyId: activeProperty?.id ?? null,
      properties,
      loading,
      setActiveProperty,
      addProperty,
      updateActiveProperty,
      refreshProperties,
    }),
    [
      activeProperty,
      addProperty,
      loading,
      properties,
      refreshProperties,
      setActiveProperty,
      updateActiveProperty,
    ],
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
