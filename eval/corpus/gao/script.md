An audiobook rendering of Study of in-plant sensing for the precise control of water use in agriculture.

<break time="0.8s"/>

ABSTRACT.

<break time="0.8s"/>

Climate change in recent years has induced extreme weather conditions that negatively impact food production and cause increased crop losses. As the world population grows, there is an emerging need to make agriculture more robust, efficient and productive. Understanding the plant dynamics becomes more important than ever for enhancing the agricultural water use efficiency (W U E), a key factor in shaping long-term agricultural development.

Plant water stress is dynamic, resulting from rapid changes in evapotranspiration (E T) due to coupling to the atmosphere and slow changes in water availability due to soil dehydration. Stem water potential (S W P) integrates the water stress across the soil-plant-atmosphere-continuum (S P A C) and is therefore useful for scheduling plant-based precision irrigation.

The micro-tensiometer can provide valuable physiological information about a plant's drought response by monitoring the plant's ability to manage its water needs when facing environmental stress. With its continuous and real-time measurements, the micro-tensiometer opens up a new opportunity to investigate system control strategies for improving W U E.

In this thesis, we study the possibility of integrating the micro-tensiometer within a water stress monitoring feedback framework for controlled water delivery to important fruit crops such as apple. We present our exploration of plants' responses to well-controlled irrigation events. We discover that the transient of root water uptake is likely to change after the growing season, resulting in increased sensitivity to daytime (more stressed state) rewatering. Additionally, we find that the plant and the soil become more decoupled as dehydration proceeds, resulting in persistent disequilibrium. The acquired data will be used to continue refining the existing hydraulic circuit models of apple under drought stress, thus finalizing a virtual representation of this speciality crop, or "digital twin". The combination of the micro-tensiometer and the model provides a valuable tool to reveal the full dynamics behind plant water stress and better agricultural water management across different phenological stages.

BIOGRAPHICAL SKETCH.

<break time="0.8s"/>

Rui grew up in Beijing, China. In two thousand fourteen, Rui began her undergraduate education at the University of Rochester. In Rochester, Rui studied under Dr. Ching Wan Tang and Dr. Alexander Shestopalov on projects related to the organic light-emitting diode (O L E D). Four years later, Rui graduated Magna Cum Laude with Highest Distinction. Continuing her exploration in the field of Chemical Engineering, Rui started her graduate study at Cornell University and conducted research under the supervision of Dr. Abraham Duncan Stroock (Chemical Engineering, Ithaca), Dr. Lailiang Cheng (Horticulture, Ithaca), and Dr. Fengqi You (Chemical Engineering, Ithaca) on the work presented in this thesis.

ACKNOWLEDGEMENTS.

<break time="0.8s"/>

This work is supported by many people and institutions, and my gratitude goes to all of them. I would like to identify here those that make the most difference on my research journey and life over the last two years and beyond: I would like to thank my advisor, Dr. Abraham Stroock, who has always been supportive and inspiring. His exceptional mentorship and insights have helped me develop into a better researcher. I would also like to thank my committee members, Dr. Lailiang Cheng and Dr. Fengqi You, who have provided invaluable assistance with my research.

I am also grateful to the Department of Chemical and Biomolecular Engineering for the diverse and inclusive environment, and to my research colleagues, Siyu Zhu, Annika Erika Huber, Corentin Bisot, Weichen Zhou, Hanwen Lu, Piyush Jain, Siyu Bu and Sahil Anand Desai, who have interacted with me daily and provided help throughout my research.

Lastly, I would like to thank my family and friends for their unconditional support and understanding throughout my life.

Chapter one. INTRODUCTION.

<break time="0.8s"/>

Section one, Context and Motivation.

<break time="0.8s"/>

Section one point one, Water Resource Utilization in Agriculture.

<break time="0.8s"/>

As the earth's most common matter and nature's universal solvent, water plays a vital role in regulating both natural ecosystems and human activities. Nevertheless, the spatial and temporal heterogeneity in the supply of water means that it can not be available to all terrestrial beings at the same degree and time. Furthermore, climate change in recent years has accelerated the rising of global temperature, the elevation of carbon dioxide concentration and the increase of variability in precipitation. These situations break the balance between the water withdrawal from the earth through evapotranspiration (E T) and water supply through precipitation. Therefore, water resource sustainability is at risk as Figure one point one presents.

Agriculture is the single largest consumer of fresh water, accounting for approximately seventy percent of all human uses. Further, irrigated agriculture contributes to more than forty percent of global food production. Yet, only half of the irrigated water is estimated to get to the intended crops. This inefficiency in water use not only impacts other natural and human water demands but can also lead to leaching of agrochemicals and run-off of irrigation water that complicate environmental pollution. In addition, the world population is projected to reach ten billion by two thousand fifty, yet the crop yields are plateauing due to increasingly limited availability of both land and water. Consequently, there is an urgent need to enhance agricultural water management to sustain the environment and satisfy the growing food demand.

To improve agricultural water use efficiency (W U E), which is measured by grain yield per unit water loss, or evapotranspiration, many studies have been conducted to better understand the water relations of plants. For instance, researchers note that maintaining slightly water deficit conditions not only conserves water, but also improves the partitioning of carbohydrate to reproductive structures, thereby encouraging fruit production. Yet, due to lack of tools to quantify the plant water status, farmers at current stage are hesitant to employ deficit irrigation to avoid harming the crops. Hence, there is a great potential value to improve the control of water inputs for the production of high quality crops and reduction of agricultural water use.

Section one point two, Water Stress Physiology.

<break time="0.8s"/>

Water stress in plants defines their growth, yield, quality, and susceptibility to diseases. According to Shackel, the stress response of the plant is a key adaptation of plant life to terrestrial existence. To examine the biology behind this response, it is of great value and importance to capture the in-plant water status.

Plant water status responds dynamically to variations in both evapotranspiration (E T) and soil dehydration. E T is defined by the environmental driving forces such as solar radiation (Q rad), vapor pressure deficit (vapor pressure deficit (V P D)) and wind speed (v wind). These micro-meteorological variables fluctuate in high frequency. Consequently, E T is a more rapid driving force (minutes to hours) of plant water stress. On the other hand, the soil dehydration is a slower process (hours to months). It depends on the soil water balance between water loss through soil drainage and water supply through precipitation and irrigation. Additionally, the plant has its own regulation mechanism via the stomata, tiny pores in leaves controlling the rate of gas exchange.

Water potential ( psi ) is used to quantify the water status in plant. The strong coupling of leaf water potential to drastic changes in surrounding environment makes it too variable to reliably represent the whole tree physiological state. Compared to leaf water potential and other plant indicators, stem water potential (stem water potential or S W P) has more stable relation to the variability in daily evaporative demands and more sensitive response to reduction in soil water content. S W P integrates the whole plant water stress level, and is therefore acknowledged to be the preferred measurement. Yet, it is difficult to capture S W P continuously.

Our current understanding of the plant water status remains incomplete, partly due to the lack of tools that can continuously and non-destructively monitor the plant responses. Herein, we use a new tool called the micro-tensiometer, an implantable water stress sensor previously developed by the Stroock group for accurate and continuous measurement of real-time stem water potential. This tool allows us to perform new physiological studies that we hope will benefit agricultural water management.

Section one point three, Challenges in Process Control and Optimization of Plant Water Use.

<break time="0.8s"/>

Precision irrigation has become increasingly important in recent years. Significant investments have been made to improve the efficiency of water delivery to crops. For instance, we have witnessed a gradual transition from traditional and inefficient surface irrigation methods such as flooding to more advanced and controlled irrigation techniques such as micro-irrigation via drip irrigation. Yet, a lack of tools with which to monitor and predict plant water status has meant that control of irrigation delivery remains primitive. Modern approaches in process control have only begun to be applied to the domain of agricultural water management. Today, most existing irrigation systems are implemented on pre-defined schedules based on practitioners' experience without even soil moisture measurements. Occasionally, the crops' water status might be checked manually using a Scholander Pressure Chamber (S P C), the widely acknowledged benchmark for water stress measurements. These methods are feed-forward (i.e. essentially open-loop) that can not respond to real-time variations in plant dynamics. This lack of effective feedback control leads to excessive water used and hinders the optimization of water management for crop outcomes such as quality and yield.

Some attention has been directed to implement control strategies that are capable of information feedback. For example, the simplest scheme to close the loop is on-off control that informs water supply when water deficiency in the soil is detected. Yet, this rudimentary scheme is problematic especially when the crop has a large response time to stress as the crop's true need for water can not be determined in time. A second strategy enacts on-off control using water balance in the root zone soil. Although this strategy accounts for weather conditions such as evapotranspiration (E T), E T and soil measurements are insufficiently reliable to define in-plant stress. This in-plant stress, when coupled with the expected future E T (estimated from the Penman-Monteith equation two five, twenty-six, entails the actual water need. In addition, woody crops such as apple trees develop stress even when plentiful water is supplied due to their significant hydraulic resistance to transpiration flow. Consequently, the soil moisture sensing cannot be easily used to infer the in-plant water status.

Table one point one summarizes the major approaches for current irrigation management.

Table one. This table compares four irrigation scheduling approaches - scheduled, soil water measurement, soil water balance, and plant stress sensing - outlining how each works and the key limitation that prevents it from being a fully reliable or practical method for managing crop water status.

Model predictive control (M P C) explicitly utilizes a model of the process of interest to define the control signal. M P C has been introduced to achieve more precise control in agricultural context. Compared to other closed-loop control strategies, the M P C-based approach can incorporate forecasts of weather (important to plants with moderate response time) and accounts for disturbances such as variations in E T and precipitation. Therefore, M P C may provide a solution for optimal plant water use in the rainfed wet environment of New York State and elsewhere if irrigation is possible.

However, the appropriateness of M P C for its use within a living system, the plant, remains uncertain. We need to establish an appropriate model entailing the plant water relations and justify the complexity of implementing M P C by comparing it with other closed-loop control strategies, for instance, the simple on-off control. Then, we can determine the effectiveness of these control strategies relative to the human expert control used today to identify the best irrigation method for the crop of interest.

Section one point four, Opportunities and Approaches.

<break time="0.8s"/>

As previously stated, model-based control only exhibits evident advantages when the model it utilizes is sufficiently accurate. The construction of the model that is physiological within the M P C framework motivates the work presented. When established, the model can be continuously informed by measurements from the in-plant sensing and climate information from nearby weather stations to refine the control on the plant for which the model serves as a digital twin as Figure one point two shows.

Further, for each crop type, there is an ideal level of water stress at which the crop can attain optimal performance to provide horticultural benefits. We need to continue conducting experiments and exploring the limits of plant drought response to improve our basis for controlling the water delivery to crops. Every new crop and new set of experiments will lead to further maturation of the models that can be fed in M P C to achieve real irrigation automation.

In summary, the micro-tensiometer could serve as a powerful tool to monitor plants' real-time drought responses, grant new possibilities to examine the transient in these physiological responses, and open up new opportunities to investigate system control strategies applicable in agricultural context for better water management.

Section two, Background.

<break time="0.8s"/>

Section two point one, Water Potential.

<break time="0.8s"/>

Water potential ( psi megapascals ) is the chemical potential of water measured in units of pressure that captures the energy state of water in plants. psi is defined as the chemical potential of water ( mu w joules per mole ) relative to the pure water at standard pressure ( mu w zero joules per mole ) divided by the molar volume of pure water (v w cubic meters per mole ) at that temperature and pressure:

Equation one point one.

There are four major components of water potential: osmotic potential (soil water potential), pressure potential, matric potential, and gravity potential (gravitational potential). These contributions add:

Equation one point two.

Usually, only one or two of the potential components play a role in any flow system. The osmotic potential measures the reduction in water potential due to dissolved solutes. The pressure potential represents the hydrostatic pressure of water relative to atmospheric pressure (P naught equals zero point one megapascals). It is negative when water is under tension in the xylem. This pressure component describes the status of water when pressure is applied to equilibrate the measuring equipment such as a tensiometer with the water in plant or soil. The matric potential represents the capillary effects or molecular interactions with most solid phases. It drives flow in unsaturated soil particles and in the cell walls of root cortex and leaf mesophyll tissues. The gravitational potential results from water being in a gravitational field.

The micro-tensiometer measures the combined effects of the osmotic potential, the pressure potential and the matric potential:

Equation one point three.

Section two point one point one, Metastable Vapor-Liquid Equilibrium (M V L E).

<break time="0.8s"/>

The phenomenon of liquids sustaining reduced pressure or tension (negative pressure) is called cohesion. While all liquids can sustain tension over some range of temperature, water has particularly high cohesive force due to the strong hydrogen bonding between its molecules. Therefore, water is more stable under tension compared to most liquids. In plant science, tension refers to the negative hydrostatic pressure that water at the top of a plant develops and is the driving force that pulls water through the vascular network of xylem. When subjected to tension, water is in a physically metastable state such that it is prone to cavitation or boiling. The principle of M V L E is applied to the design of a micro-tensiometer (Chapter two Section two).

Section two point two, Soil-Plant-Atmosphere Continuum (S P A C).

<break time="0.8s"/>

Soil-plant-atmosphere continuum (S P A C) describes the journey of water flow from the bulk soil, through the plant, to the atmosphere, driven by a gradient in water potential (Figure one point three). The plant acts as the interface connecting the soil and the atmosphere and relies on water to remain hydrated. The soil is the source of water for this continuum and has higher water potential (less negative), whereas the atmosphere is the sink and has lower water potential (more negative).thirty-three, thirty-four This concept of water transport through S P A C can be traced back to one thousand nine hundred forty-eight by Van den Honert and the central part of it, the cohesion-tension (C T) theory, goes back to Askinasi, Dixon and Joly from the eighteen nineties.

The use of S P A C models to quantify plant water status and water fluxes has been widely adopted in agricultural and plant physiological studies. Different research groups have devised different circuit models of S P A C with focus on different compartments. For instance, the Simmons group in Australia focuses on modeling the soil for the study of hydrology. On the other side, the Katul group at Duke University examines the top portion of the S P A C to emphasize the importance of leaf canopy and atmosphere boundary layer. We work on S P A C models that are centered at the plants to explore the physical and physiological responses to changing environmental demands and soil conditions that can be validated by the in-plant sensing with the micro-tensiometer. We use S P A C models as avenues to interpret and predict the plant dynamics.

Section two point two point one, Water Transport in Xylem.

<break time="0.8s"/>

Inside the plant, the mechanism of water transport in the stems from the root to the leaf happens mainly through the xylem. This mechanism was first proposed as cohesion-tension theory. The xylem wall is a hydrophilic surface. Due to the strong intermolecular interactions between it and the water molecules, water can be pulled from the root to the leaf through capillarity under negative pressure that is created at the evaporating sites in the leaf.

Further, the movement of liquid water through the xylem is under metastable state. This is a fragile process with respect to interventions.The tendency for gas bubbles to form within the water column increases with increasing tension that could result in cavitation (boiling) or embolism (entry of air from adjacent tissues). This loss of continuity of the liquid path disrupts water transport.

Section two point two point two, Soil-Root-Leaf Water Relations.

<break time="0.8s"/>

As noted by Niklas, water applies its vital capacity as a universal solvent to enable living plant roots to absorb minerals from the soil. Different soil types have different water holding capacities and the water movement is driven from the more saturated soil to the less saturated soil (around the rye-zo-sphere) down a gradient in water potential. The rye-zo-sphere is taken as the root-zone soil that is in close contact with the roots.

Figure one point four presents a hypothetical dehydration process. In theory, the plant water potential at the root and leaf could progressively relax back (becoming less negative) to reach equilibrium with the soil water potential at predawn even during a dehydration process. The evaporating surfaces in the leaf create a gradient from the root (less negative in water potential) to the leaf (more negative in water potential). Midday water potential represents the lowest water potential measured during the day and corresponds to the most stressed state, whereas the predawn water potential indicates the most relaxed state in the measured diurnal. During nighttime, the leaves receive no sunlight so the stomata, tiny pores in the epidermis of the leaf, are mostly closed. Therefore, the transpiration and uptake of carbon dioxide via the stomata are halted.

Section two point two point three, Stomatal Regulation.

<break time="0.8s"/>

The evaporation from the leaf could occur from the leaf xylem conduits, the mesophyll cell walls, or the tissue around the stomata. Yet, evaporation from a leaf's interior is significantly inhibited by the cuticle that covers the leaf. Therefore, water can mostly diffuse to the atmosphere through the stomata (Figure one point five). The stomata regulate the gas exchange between the plant and the atmosphere through water transpiration and carbon assimilation (photosynthesis), thereby directly affecting the plant's vegetative growth and reproduction. They open during the day in response to sunlight to start photosynthesis and generally close at night.

Understanding how the plant regulates its stomatal conductance (g s) is crucial for furthering the study of plant drought response and refining the construction of S P A C models (Chapter one Section two point two point four). Yet, the precise mechanism underlying this regulation is still not well understood, largely due to the complexity of the stomata's responses to both environmental and internal biological variables. With the capability to measure the plant water stress in situ, the micro-tensiometer can shed light on the mechanism behind stomatal regulation by, for example, capturing the stomatal oscillations through measurement of stem water potential.

Section two point two point four, Construction of Circuit Models of the S P A C.

<break time="0.8s"/>

S P A C models utilize a circuit analogy for the water flow with evapotranspiration (E T kg s minus one ) as the current source (Figure one point six). E T is related to solar radiation, Q rad, in micromoles per square meter per second, vapor pressure deficit, V P D, in kilopascals, and wind speed, v wind, in meters per second,. These environmental variables vary with high frequency. Therefore, E T is a rapid driving force of plant water stress. V P D is calculated from the relative humidity, in percent relative humidity, and temperature, T, in degrees Celsius, of air, using Equations one point four and one point five:

Equation one point four.

Equation one point five.

Due to difference in water stress, water flow is driven across successive compartments of the continuum such that it either evaporates from the soil or transpires through the leaves, where stomatal conductance (g s) is an important factor affecting the transpiration.

Capacitance (C) represents the dynamic water storage capacity of the respective compartment and resistance (R) signifies the viscous resistance to the flow of water through this compartment. The product of R and C entails the timescale ( tau ) of the transient. Previous study shows that a simple circuit consists of a pair of hydraulic capacitance (trunk capacitance) and resistance (trunk resistance) of the trunk is sufficient for elucidating the response of an apple tree to environmental driving forces in wet environment (well-watered condition).

An additional compartment is needed to elucidate the apple tree in water-stressed condition when the importance of rye-zo-sphere and soil hydraulic properties becomes more evident. A soil compartment is added to explore the long transient impact of soil dehydration on plant water stress during dry-down. Soil depletion during this time could trigger significant increase in the soil hydraulic resistance (soil resistance) and capacitance (soil capacitance) because these constitutive properties have highly nonlinear dependence on soil water potential, as described below.

Currently, we use two-compartment model to represent the apple tree in water-stressed condition, featuring the plant compartment (saturated porous media) with constant R t and C t as well as the soil compartment (unsaturated porous media) with varying R s and C s. In addition, the rye-zo-sphere resistance (rhizosphere resistance) in the soil compartment represents its resistive flow against water from the bulk soil to the roots. The governing equations for the two-compartment model depicted in Figure one point six are essentially two unsteady-state mass balances, represented by the nonlinear ordinary differential equations:

Equation one point six.

Equation one point seven.

where s is the abbreviation for soil; t for trunk where S W P is measured; and r for rye-zo-sphere. I is the irrigation that rehydrates the soil. E T is the modeled evapotranspiration that drives water stress and will be illustrated below.

Equation one point six represents the relatively simple plant compartment based on the assumptions: - No cavitation in the xylem tissue under the studied stress range. - No parallel path of water flow through the xylem.

We use the Penman-Monteith equation, references twenty-five and twenty-six, to estimate E T:

Equation one point eight.

where lambda equals two point two six times ten to the power of six joules per kilogram, is the latent heat of vaporization; S, in pascals per degree Celsius, is the slope of saturation vapor pressure curve with respect to temperature; rho a kilograms per cubic meter and C p equals one point zero one times ten three joules per kilogram are the density and heat capacity of dry air, respectively; gamma equals sixty-six pascals per degree Celsius, is the psychrometric constant that relates the partial pressure of water vapor in air to the air temperature; r a, in meters per second, is the boundary layer resistance and is proportional to the inverse of v wind. seventeen Empirical models for g s are taken from Jarvis and Thorpe. Thorpe's model considers g s under well-watered conditions for potted apple trees. Jarvis' model considers the effect of plant water potential on stomatal response and we adopted the following dependence for modeling the waterstressed conditions:

Equation one point nine.

where g max, in meters per second, is the conductance at maximum opening; and alpha g, in per pascal, and beta g, in micromoles per square meter per second, are the parameters determining the dependence on V P D and photosynthetically active portion of solar radiation (Q P A R), respectively. Q P A R is the photosynthetically active portion of solar radiation (Q rad). wilting point water potential is the wilting point water potential and gamma g determines the onset of this dependence on S W P as the plant develops stress. Based on Jarvis' correlation, g s does not have a strong dependence on S W P for stem water potential greater than or equal to wilting point water potential, i.e., when the plant is not stressed. However, as dehydration proceeds and the stress intensifies, the stomata will shut in response to low S W P to prevent further damaging the plant such as wilting.

On the other hand, the soil compartment, represented in Equation one point seven, is much more complex because it is highly nonlinear. The soil compartment is mainly defined by five independent parameters: the saturated soil water content ( theta s), the residual soil water content ( theta r), the inverse of air entry potential ( alpha ), the shaping factor (n) of the water retention curve and the effective soil volume (V soil). The construction of the soil compartment takes the following assumptions: - Soil evaporation is negligible. - Water entry is uniform across the root zone. - Root architecture is uniform with constant root length density. - Active roots share identical local geometry.

The process of root water uptake from the bulk soil and through the rye-zo-sphere along a gradient in water potential is directly affected by the soil and rye-zo-sphere properties. These properties are highly nonlinear functions of the soil water potential and we can derive them from the soil water retention curve ( theta (soil water potential)).

The soil water retention curve describes the dependence of the relative water content ( theta ) on the soil water potential:

Equation one point ten.

Equation one point eleven.

where alpha s, in per centimeter, is the inverse of the air entry potential, or the "bubble point"; m s and n s are empirically-defined constants that define the shape of the water retention curve; theta, in cubic centimeters per cubic centimeter, is the absolute volumetric soil water content; theta r is the residual soil water content which refers to the remaining water in soil after oven dried; and theta s is the saturated soil water content.

Figure one point seven shows the typical form of theta (soil water potential), a highly nonlinear function. Consequently, a small change in the soil water potential induces a significant change in the soil water content that complicates the modeling process of the soil compartment.

By treating each root as a cylindrical tube of radius r one cm surrounded by a cylinder of soil of radius r two cm and assuming the water movement is radial from the bulk soil, we can represent the soil resistance, R s, in megapascals seconds per kilogram, and the soil capacitance, C s, in kilograms per megapascal, as:

Equation one point twelve.

Equation one point thirteen.

where r two is the typical half distance between roots; r one is the root radius; V soil, in cubic centimeters, is the bulk soil volume; R L D, in centimeters per cubic centimeter, is the root length density; K is the soil hydraulic conductivity; and C s,sat, in kilograms per megapascal, is the soil capacitance at saturation given by:

Equation one point fourteen.

The rye-zo-sphere resistance, R r, in megapascals seconds per kilogram, is inversely proportional to the effective soil water content and dependent on the root membrane resistance, R r,sat, in megapascals seconds per kilogram, which is taken as a constant value in the current model. Following Gardner's contact model, we represent R r as:

Equation one point fifteen.

Figure one point eight describes the different nonlinearity experienced by the soil compartment. The soil resistance varies more rapidly with the soil water potential. Nevertheless, the rye-zo-sphere resistance (rhizosphere resistance) that represents the resistive force against water flow from the bulk soil to the roots remains more significant.

Accompanying the in-situ measurements from the micro-tensiometer, we use these hydraulic circuits to attempt to build predictive models of the dynamic responses of the stem water potential to changing environments across a range of stress conditions. The constructed models can also instruct physiological studies. For instance, according to other researchers, the deviation of simple RC models from the dynamic plant responses to perturbations in evaporate demand can shed light on factors such as the dynamic changes in stomatal conductance in controlling plant water flow.

Section two point three, Micro-Tensiometer.

<break time="0.8s"/>

The micro-tensiometer was designed to probe the dynamic water stress in vascular plants continuously and accurately. Figure one point nine presents the working mechanism of the micro-tensiometer. A micro-tensiometer has three major components: a reservoir (also referred to as cavity in later context) filled with pure water, a nanoporous silicone membrane connecting the internal water to the external environment of interest, and a pressure-sensing diaphragm in the cavity to measure the pressure of the reservoir. The working mechanism will be further illustrated in the coming context.

The micro-tensiometer can measure tension as low as minus ten megapascals before cavitation. With this range of stability, the micro-tensiometer is eligible for capturing the stem water potential of living plants that have a typical range greater than or equal to three megapascals. In addition, the response time of a micro-tensiometer is about a minute which is much less than that of, for instance, a living apple tree. Therefore, the micro-tensiometer is capable of capturing the full plant dynamics. In addition, both greenhouse and field testing have showed a linear correlation between the micro-tensiometer and the widely accepted Scholander Pressure Chamber (S P C).

In the following subsections, we overview: one) the micro-electrical-mechanical system (M E M S) design of the micro-tensiometer; two) the incorporation of tensiometry to the design; and three) other commercially available water potential sensors to further demonstrate the value of the micro-tensiometer for accurate stem water potential measurements. The fabrication, packaging, calibration and embedding methodology of the micro-tensiometer will be described in Chapter two. For more detailed information, we refer to several studies

Section two point three point one, Micro-Electrical-Mechanical System (M E M S).

<break time="0.8s"/>

Micro-electrical-mechanical system (M E M S) is a well-established technique to build devices of micro-scale from a system of electrical and mechanical components using micro-fabrication technologies.

The micro-scale pressure sensing component of the micro-tensiometer is derived from existing piezo-resistive-M E M S-diaphragm pressure sensing technique, where the piezo-resistive strain gauge is a common type of pressure sensors. It translates the mechanical stress to an electrical signal through a diaphragm attached with piezoresistors. In response to the stress applied on the diaphragm, the electrical resistance of the resistors changes.

Section two point three point two, Tensiometry.

<break time="0.8s"/>

Figure one point ten presents the concept of tensiometry. A water reservoir is connected to the outside through a layer of porous membrane. In saturated sample, no capillary tension is generated in the liquid water phase, so the hydrostatic pressure of the liquid is the same as the atmospheric pressure. However, exposure to sub-saturated external phase drives the water out of the device (Figure one point nine) such that the hydrostatic pressure in liquid water is reduced relative to the external pressure. This difference in pressure induces a mechanical deflection of the diaphragm in the cavity and generates strain in a Wheatstone bridge (B R) of piezoresistors; the state of strain is measured as a voltage across the bridge. Importantly, this pressure difference is maintained by the menisci at the pore openings.

By incorporating conventional tensiometry and nano-porous silicon membrane into a microelectro-mechanical system, the micro-tensiometer extends the range of water potential to physiological range and shrinks traditional device to enable embedding to living plants for the study of plant transient responses that can also be used to infer the soil and the canopy water status.

Section two point three point three, Other Available Water Potential Sensors.

<break time="0.8s"/>

Although there are other existing plant sensors, none seems suitable for irrigation scheduling or provides continuous measurement for exploring the full plant dynamics at current stage.

earlier studies introduced a breakthrough technology in the nineteen sixties to measure in-plant water potential. The Scholander Pressure Chamber (Figure one point eleven (c)) operates on pressurizing a cut leaf (bagged over some time to stop leaf transpiration if measuring the stem water potential) until water bubble is seen on the cut end. The gas pressure inside the chamber at the moment is equal to the negative of the leaf water potential. Though appropriately accurate ( plus or minus zero point one megapascals), this method is manual and invasive that is unsuitable for irrigation control which requires frequent monitoring and information feedback.

Psychrometers have been used to measure in-plant water potential continuously by using the difference between dry bulb and wet bulb temperature to measure the relative vapor pressure of the gas in equilibrium with the sample. Nevertheless, they have proven to be complex and unreliable for long-term (weeks to months) use. Their operation is intrinsically a non-equilibrium process. Measurements with psychrometers can also generate large errors when large temperature gradients are present.

Other plant-based measurements such as leaf turgor or sap flow sensors do not directly capture the plant water stress. In summary, the micro-tensiometer, with its capability to accurately probe the in-plant water stress, opens up new opportunities for physiological studies and engineering applications that will be further illustrated.

Section two point four, Process Control.

<break time="0.8s"/>

To achieve automation in a process operation, it is important to take corrective actions in a timely manner. Control is a management that uses measurements of the process inputs or outputs to properly tone the process inputs, thereby completing the correction in a process. Figure one point twelve compares the two widely used types of control: the feedforward control (based on measurement of inputs) and the feedback control (based on measurement of outputs).

The major distinction between the feedforward control and the feedback control is whether the process outcome plays a role in the control strategy. Feedforward control is future-directed: it anticipates deviations in advance. A feedforward controller will try to suppress the disturbance by changing the manipulated input before the system output is affected by that disturbance. Consequently, the feedforward control is considered an open-loop system, lacking the ability to respond to the actual state of the process. Since the response to the control signal is in a pre-defined way and anticipation about the future outcome is unlikely to be comprehensive, the feedforward control may exhibit error accumulation.

In contrast, feedback control is error-based, taking action after deviations are detected. A feedback controller will evaluate the system's past behaviors and try to improve similar activities in the future trajectory. One shortcoming of feedback control is that it can not correct a deviation from setpoint at the time of detection, an effect that feedforward control can, in principle, achieve. Therefore, the combination of feedforward control and feedback control can achieve a better control result than either strategy acting alone. Additionally, the feedback control is also known as closed-loop control as the control action from the controller depends on the feedback information from the process output. A simplified representation of a closed-loop control block diagram is shown in Figure one point thirteen.

Our hydraulic circuit model (Chapter one Section two point twenty-four) can be compared with the block diagram of a control system to define an appropriate model for control. Using the simplest one-compartment model as an example: the system output (y) is the stem water potential; tau p is the time constant associated with the transient that is calculated from the product of the trunk resistance and capacitance (trunk capacitance) when the system is connected to saturated soil so the stem water potential can relax exponentially back to the soil water potential during nighttime. A measure of the time delay between the input (u) and y, which is called process deadtime ( theta p), is needed for our system. More specifically, theta p is associated with the delivery mechanism such as the time needed for water to be absorbed from the soil by the root after an irrigation event. Further, theta p can be considered as a simplification of another physical phenomenon that has transient, for instance, the transient experienced by the soil compartment can be lumped into theta p.

Section two point four point one, On-Off Control.

<break time="0.8s"/>

In the hierarchy of closed-loop control strategies, an on-off controller is the most rudimentary strategy to achieve feedback. As its name entails, a system will turn on when the output is lower than the desired setpoint, and turn off when the output exceeds the setpoint. However, a major problem associated with an on-off control strategy is that the controller may become unstable and constantly open and close the system, thereby disturbing the system.

Section two point four point two, Proportional-Integrator-Derivative (P I D) Control.

<break time="0.8s"/>

The Proportional-integrator-derivative (P I D) control is another common closed-loop control strategy. It consists of three tuning parameters which are the proportional (P), integral (I) and derivative (D) of the error term. Equation one point sixteen outlines the time-domain representation of a P I D controller.

Equation one point sixteen.

where K p is the proportional term that is applied to the current stage of the error. When the actual process output is not able to attain the desired setpoint change, offset occurs. Such a problem is often associated with a proportional-only controller as in reality the output of the controller and the process reach new equilibrium before the error is eliminated, stressing the need for additional control terms. K I is the integrator term that accounts for the process history by integrating the past values of the error over time. Oftentimes, a derivative term, K D, is added to consider the error's current rate of change. Using this knowledge of the derivative of the error grants the controller ability to predict the direction of future error and thereby better compensate for it.

The applicability of P I D controller depends on the fine tuning of these three parameters. However, when the P I D controller is tuned aggressively, overshoot of the setpoint can occur, resulting in oscillations of the system output. An oscillatory response is highly undesirable in processes that require precise control such as in the regulation of blood glucose level in the context of closed-loop diabetes treatment.

Section two point four point three, Model Predictive Control (M P C).

<break time="0.8s"/>

A more sophisticated strategy that has advanced in recent years is called the model predictive control (M P C). M P C explicitly utilizes a model of the system process to define the control signal. As illustrated in Figure one point fourteen, the M P C control algorithm optimizes the profile of the manipulated input variables based on a forecast of process disturbances over a finite future time horizon to maximize (or minimize) an objective function subject to the process models and constraints. Therefore, M P C can more reliably account for future system behaviors compared to classical feedback control strategies such as P I D control. Further, because of the presence of this prediction horizon, M P C is particularly valuable when used in system displaying large time delays. In the irrigation management context, for example, the decision about irrigation amount can benefit from the presence of prediction horizon. The plant or crop can possess considerable response time to irrigation. If weather forecast entails precipitation in the projected prediction horizon, the irrigation amount at current time can be reduced without posing harm to the crop.

In our application, the process model is the S P A C model of the crop of interest and M P C is implemented to inform current irrigation decision by accounting future predictions on important variables such as weather and disturbances such as precipitation. However, as model-based control only exhibits evident advantages when the model it utilizes is sufficiently accurate. We need to continuously refine the model by comparing it with the in-plant sensing via the micro-tensiometer. In addition, we need to further understand the plant responses and establish a way to interpret the dynamics so we can apply control on a living system that is controlling itself.

Our goal is to understand our process (S P A C) better so we can assess the value of these different strategies for the control of plant water status. The next chapters are dedicated to illustrate our use of the micro-tensiometer to further this end. We will discuss the methodology associated with preparing the micro-tensiometer in Chapter two and present the field study using the micro-tensiometer in Chapter three.

Chapter two. MATERIALS AND METHODS.

<break time="0.8s"/>

Section one, Introduction.

<break time="0.8s"/>

The design and study of the micro-tensiometer were previously published by the Stroock Group. The micro-tensiometer (overviewed in Chapter one) merges the technologies of microelectrical-mechanical system (M E M S) design and micro-fluidic device design, and utilizes the theory of metastable vapor-liquid equilibrium (M V L E). In this chapter, we first demonstrate the fabrication, packaging, calibration and embedding methodology of the micro-tensiometer. Further detail can also be found in Zhu. Then, we discuss the construction of an irrigation control system with the micro-tensiometer. Lastly, we introduce our methods for data analysis that provide the foundation for result discussion in Chapter three.

Section two, Micro-Tensiometer Preparation.

<break time="0.8s"/>

Section two point one, Fabrication.

<break time="0.8s"/>

The micro-tensiometer was prepared by double-sided fabrication on a silicon wafer (p-type; one-one-one crystal orientation silicon wafer, Addison Engineering, Inc.). The current device design has dimension of five millimeters by five millimeters by eight hundred micrometers. The frontside consists of a platinum resistance thermometer (P R T) and a Wheatstone bridge (B R) to sense the temperature and the water potential of the system of interest, respectively. The B R has four piezo-resistive strain gauges. The backside is formed with an etched cavity and nanoporous silicone membrane and is bonded with a glass wafer (Borofloat thirty-three glass wafer, University Wafer) to enclose the water reservoir.

The fabrication was performed in the cleanroom of the Cornell NanoScale Science and Technology Facility (C N F). The major micro-fabrication processes are graphically overviewed in Figure two point one and can be retrieved from prior studies and Zhu.

Briefly, they include: Furnace growth of insulating oxide, silicon dioxide, layer; deposition and patterning of poly-silicon (polyS i) resistors; patterning of silicon dioxide insulation layer; etching and patterning of backside cavity and microchannels; electrochemical etching of nanoporous silicon (PoS i) membrane; anodic bonding of the silicon wafer to a borofloat glass wafer; fabrication of frontside electronics: platinum (Pt) with titanium (Ti) adhesion layer; deposition of passivation layers and dicing.

Section two point two, Packaging.

<break time="0.8s"/>

After the diced wafers were taken out of the C N F, the individual sensors need to be packaged for data acquisition and protection against mechanical damages and corrosion. Figure two point two (a) shows a micro-tensiometer mounted onto a printed circuit board (P C B, OSH Park). The other ends of the wires attached to the P C B were soldered to male and female connectors (Waterproof DC Power Cable Set, Adafruit) to connect to a set of a datalogger (CR six, Campbell Scientific) and a Multiplexer (AM one six over thirty-two B, Campbell Scientific) for data acquisition.

The external wiring, American Wire Gauge twenty-eight, require the micro-tensiometer to first be glued onto the P C B. The newly adopted glue is a soft die attach (Dow Corning three thousand one hundred forty RTV), which is silicone-based that has low shear modulus of zero point zero two gigapascals to minimize the possible deformation of the sensor due to swelling of the P C B. Then, we used the wire-bonding technique at the C N F to connect the platinum pads on the micro-tensiometer and the copper pads on the P C B using twenty-five micrometer-thick aluminum wires. The wire-bonds were the most fragile part, therefore a wire-bonding protection material (nine thousand one-E-v three.one, Dymax) that features minimal adds-on stress was applied and cured with UV and thermal treatment before further encapsulation.

The assembled device was enclosed in an aluminum tube (Figure two point two (a)). Aluminum is thermally conductive and facilitates the thermal contact with the plant tissue after embedding (Chapter two Section two point four). This aluminum cylinder was then filled with one of two potting materials: the base potting material was polyurethane resin UR five zero four one (ELECTROLUBE) in a weight ratio of three point six four to one. Polyurethane has high resistance to tearing and passage of osmotic solutions to protect the sensor from mechanical stress during embedding and from corrosion induced by aqueous solutions in the environment. However, the thermal expansion nature of the polyurethane sometime leads to disturbed signal on the Wheatstone bridge (B R) when the material touches the sensor diaphragm as seen in undesirable drift in the bridge offset response during temperature calibration (Chapter two Section two point three point one); this response could also affect the sensor reading reliability during field installation.

A gel-like encapsulant (Sylgard five hundred twenty-seven) in a weight ratio of one to one was added on top of the polyurethane potting to provide full coverage of the electronics (B R and P R T) to further stabilize them when exposed to complex external environment. Sylgard five hundred twenty-seven is also silicone-based, providing relatively low stress packaging that minimizes the sensor bridge response to thermal and mechanical perturbations. However, the low viscosity of this material complicates the potting process as the majority of Sylgard five hundred twenty-seven drained due to gravity before heat cure. For this reason, a combination of two types of potting materials was used. The polyurethane was potted at the bottom, covering the electronic connections, to provide a good seal and osmotic resistance. The silicone was potted till the top by fine controlling the potting amount to ensure it not touch the Si-glass interface that blocks the porous silicon membrane, removing unnecessary stress on the sensor and thoroughly protecting the on-chip electronics.

Section two point three, Calibration.

<break time="0.8s"/>

Calibration was then performed to translate the voltage output, in millivolts per volt, from the micro-tensiometer into pressure, in bars, for the bridge response and resistance output, in ohms, into temperature, in degrees Celsius, for the P R T. A set of CR six datalogger and a multiplexer (Campbell Scientific) was used to record the sensor response during the calibration processes with each set enabling connection to eight mu TMs. The datalogger was programmed in C R Basic Editor (Code in Appendix five point one).

To prepare the micro-tensiometer for use, the sensors were first filled with DI water under high pressure. The mu TMs were placed in high pressure chambers (HiP High Pressure Equipment Company) filled with water at eight hundred pounds per square inch for more than eight hours to push the water through the porous silicon membrane into the cavity. The filled sensors were then processed for temperature calibration and osmotic calibration.

Section two point three point one, Temperature Calibration of Bridge Offset and P R T.

<break time="0.8s"/>

For the temperature calibration, the PRTs on the mu TMs were calibrated against a commercial P R T (HSRTD, OMEGA Engineering, Inc.) measured in degrees C in a LabVIEW controlled water bath (Thermo Fisher Scientific). During the process, the variation of the bridge offset with respect to temperature was also recorded to correct for the temperature effect on the bridge output. The bridge offset is the sensor's voltage output when it is submerged in pure water that can be either negative or positive. Figure two point three (a) shows the transient temperature responses of a sensor (used in Summer two thousand twenty) during a full cycle of temperature calibration that was set from fifteen degrees C to thirty-five degrees C with an increment of five degrees C and held one hundred fifty mins at each setpoint to reach thermal equilibrium between the mu TMs and the water bath.

The data of the P R T response and bridge offset response were then fit by linearly regression following Equations two point one and two point two, respectively:

Equation two point one.

Equation two point two.

These calibration results are presented in Figure two point three (b) and (c), respectively where the P R T calibration coefficients, m T, in degrees Celsius per ohm, and b T, in degrees Celsius, and B R offset calibration coefficients, m P T, in degrees Celsius millivolts per volt, and b P T, in degrees Celsius, can be obtained as the slopes and intercepts of their respective curves.

Section two point three point two, Osmotic Calibration of Bridge Response.

<break time="0.8s"/>

After the temperature calibration, the filled sensors were calibrated against step changes in pressure. Each micro-tensiometer was dried and sealed in a custom-made glass cap (top end covered with expanded P T F E membrane) that inhibits entry of liquid and grants water vapor transfer. The sealed mu TMs were then placed in different osmotic solutions with known water potentials to relate the bridge responses to values in water potential after equilibrium was reached. This transfer step needs to be fast to avoid sensor cavitation when exposed in dry air over a minute.

The osmotic solutions were made by mixing Urea (Sigma-Aldrich) with DI water. The water potentials of the solutions were measured using a Dewpoint PotentiaMeter (WP four C, METER). Four Urea solutions (from the most to the least negative in water potentials) and DI water (zero water potential) in this order were used. The devices were left in the first solution for more than six hrs to thoroughly dry the water residues inside the capped mu TMs; equilibration in the subsequent solutions normally took less than two hrs per solution as assessed when bridge response stabilized. During the process, the solution containing the mu TMs to be calibrated was well-insulated to minimize temperature gradients between the solution and the sensor.

The transient bridge response to changes in solutions is displayed in Figure two point four (a). The data of bridge response was then fit by linear regression following:

Equation two point three.

The osmotic calibration coefficients, b P bar and m P bar, in volts per millivolt, together with the coefficients obtained from the temperature calibration were used in Equation two point four, which outputs the temperature-corrected pressure in bars (converted to the conventional unit in megapascals in the following context) that a micro-tensiometer measures.

Equation two point four.

The calibration code implementing Equations two point one - two point four to generate the calibration coefficients is attached in Appendix five point two.

Section two point three point three, Uncertainty Assessment.

<break time="0.8s"/>

As the described calibration processes are manual, uncertainty in both the measuring equipment and the calculated (or measured) quantities exist. Here, we overview the steps that can generate uncertainty (denoted e X with X representing the source of uncertainty) and further detail can be retrieved from Black.

To begin with, there are uncertainties reported by the manufacturer. The CR six datalogger acquires signals from the micro-tensiometer by applying an excitation voltage to its full bridge and then obtain a differential voltage measurement of this bridge output. Therefore, both the voltage excitation applied and the voltage measurement performed by the CR six datalogger possess uncertainties (e vin equals plus or minus one point seven millivolts). In addition, for the temperature calibration, there is uncertainty associated with the commercial P R T (used for obtaining the temperature of the water bath). For the osmotic calibration, there are uncertainties associated with the preparation of the osmotic solutions. Both the mass balance (used for weighing the solute) and the WP four C meter (used for measuring the water potential of the osmotic solutions) have reported uncertainties (e M equals plus or minus zero point zero zero one grams; and e psi equals plus or minus zero point one megapascals).

Further, uncertainty in the calculated quantity (f) can be determined by propagation of errors. Assuming all relevant parameters to calculate the uncertainty associated with f are independent, e f can be assessed:

Equation two point five.

where e f is the uncertainty in the calculated quantity f; e x i is the uncertainty in the independent parameter x i that affects f; and the partial derivative of f with respect to x i is evaluated for each value of x i. This error propagation is used to obtain the uncertainty in, for example, P R T measurements by the CR six that depend on the ratio of voltage outputs from the P R T and that from a reference resistor with known resistance, in ohms,.

Section two point four, Embedding.

<break time="0.8s"/>

After calibration, the mu TMs were ready for field installation. The individual sensor was embedded into the active xylem of the plant of interest, as presented in Figure two point five.

For an apple tree, the active xylem is usually five to twenty millimeters deep from the outside surface after the bark is removed. Additionally, the outer portion of the xylem has higher water transport rate compared to the inner portion. Therefore, the bottom of the drilled hole is chosen to be at a radial distance of five millimeters from the surface beneath the bark. The embedding procedure (Figure two point six) is as follows: A seven over sixteen" cork bore (HUMBOLDT MFG CO) was used to cut off the phloem (Figure two point six (a)). A custom-built sleeve (FloraPulse Co.) with a vent hole was then hammered into the tissue and stopped when its bottom touched the xylem (Figure two point six (b)). A seven point nine millimeters (five over sixteen") diameter four-flute endmill drill bit (McMater-Carr) was used to drill a hole five mm radially into the tissue. During the drilling process, the hole was constantly moisturized and cleaned with DI water.

Mating compound was necessary to maintain the liquid contact and thermal equilibrium between the tree tissue and the micro-tensiometer. Following previous work by Michael Santiago (FloraPulse Co.), we used Kaolin (powder, Sigma-Aldrich) paste in water as the mating compound. Kaolin contains mainly hydrous aluminosilicate that has a good thermal conductivity, fourteen watts per meter per kelvin, and is therefore an appropriate mating compound to facilitate thermal equilibrium. The Kaolin paste was prepared by mixing with DI water to form a volume ratio of roughly forty-eight point five percent. The drilled hole was half-filled with mating compound (Figure two point six (c)). Additional Kaolin paste was applied directly onto the porous silicon interface of the packaged sensor to further ensure the liquid and thermal equilibrium between the micro-tensiometer interface and the active xylem tissue after embedding.

The micro-tensiometer, attached with a spring (McMASTER-CARR Part No. nine six five seven K two eight six ) as shown in one point one one (b), was pressed into the sleeve. Then, the matching aluminum cap was attached to ensure the sensor inside the sleeve was constantly in contact with the xylem tissue. Excessive mating compound was extruded through the up-facing vent hole after the sensor was pressed in (Figure two point six (d)).

Then caulk (Silicone one, GE) was applied around the sleeve and the vent hole to provide a waterproof seal (Figure two point six (e)).

five layers of two" x four" parafilm (Bemis Company, Inc) were wrapped around the enclosed sleeve (Figure two point six (f)) to stabilize the inside micro-tensiometer around the trunk and provide waterproof support.

Plastic wraps (Figure two point six (g)) were then added to further secure the sensor and protect it from moisture. A zip-tie was applied tightly around the bottom of the wrapped sensor to prevent it from rotational movement, thereby avoiding potential mechanical stress caused by the following steps where layers of warp foam (Figure two point six (h)) and bubble foam (Figure two point six (i)) were added to provide further thermal insulation.

Finally, a dense foam box covered with aluminum foil was used as the final layer of thermal insulation (Figure two point six (j)). The aluminum foil provides reflective insulation to prevent concentrating intense radiation onto the sensor and damage its electronics.

Section three, Field Experiments.

<break time="0.8s"/>

Section three point one, Growth Information of Apple Trees.

<break time="0.8s"/>

The potted apple trees were on M.twenty-six semi-dwarfing rootstock with "Royal Gala" scion in sand (Acknowledgement of Dr. Cheng for the apple trees). Their trunk sizes were three to four centimeters in diameter and they were two to two point five m in height. The sand in the pot was approximately twenty-nine point two centimeters deep and the inner diameter of the pot was thirty-six centimeters.

In two thousand nineteen, they were moved out of the Greenhouse to the Cornell Orchards on May twentieth and, after the experiments stored in the nearby white tent for their dormancy. The experimental period was from the end of July two thousand nineteen to mid-September two thousand nineteen. In two thousand twenty, four remaining trees (referred to as T one - T four ) were moved from the white tent to the same set at the Cornell Orchards on July thirtieth. Experiments were conducted from the beginning of September two thousand twenty to mid-October two thousand twenty. The trees had apples growing during the period. This thesis focuses on analyzing the data obtained from two (T one & T two ) of the trees during two thousand twenty Experiments (T three had broken bridge, leaving only P R T sensing and T four had frequent drift in bridge response before predawn). We refer to the Dissertation of Siyu Zhu for Summer two thousand nineteen setup and results.

After the experiments, the leaf areas of the potted apple trees were measured using a leaf area meter (LI-three thousand one hundred C). For each tree, one hundred fifty fresh leaves were taken as a sample and measured directly with the leaf area meter. Both the sampled leaves and the rest unmeasured leaves were then thoroughly dried in an oven. The total leaf area was calculated based on the dry-weight ratio of the measured sample to the total. The total leaf area for each tree measured at the end of the experiment was approximately two m squared.

Section three point two, Design of Irrigation Control System.

<break time="0.8s"/>

To achieve the integration of the micro-tensiometer and effective control in the experiments, an automated system was needed to enable actions such as remote issuing of water, acquisition and visualization of field data.

A control box with a Raspberry Pi (model three B+) and a four-channel relay module (five V) controlling four solenoid valves (twenty-four VDC) was utilized in Summer two thousand nineteen (Acknowledgement of Corentin Bisot for the initial design). This control box was refined for Summer two thousand twenty experiments (Acknowledgement of Weichen Zhou for redesigning). In this thesis, we illustrate the functions of the irrigation control system in Summer two thousand twenty with emphasis on changes from the previous version.

Figure two point seven provides the set overview in Summer two thousand twenty. The electronics interference previously observed was minimized by distributing roles between different Pi-based micro-controllers into a data center and a control center. The issue with hardware break-down due to power shortage from the solar panel during extended cloudy days was resolved by switching to wall plug in the nearby shed via extension cords. Future refinement is needed to find solutions to provide continuous power to the system, leaving minimal dependence on the field facility to achieve higher system versatility.

As foreshadowed, in Summer two thousand twenty, the irrigation control and data acquisition were separated to avoid any potential electronic interference. Consequently, two Raspberry Pi were used: one served as the control center (referred to as control Pi) to launch the irrigation by remotely actuating the valves, twenty-four volts AC, Rain Bird, via relays, the other served as the data center (referred to as data Pi) to store locally and transmit online the micro-tensiometer data, the soil and scale data, and the weather station data via serial communication with the CR six dataloggers. Both Pis relied on three G dongle (Hologram NOVA) for cellular communication between each Pi and laptop, as well as the online Internet of Things (I O T) (Internet of Things) platform. We transitioned from Ubi-dots to Things Board, an open source I O T platform for more direct visualization and is cost free.

We could remotely access the two Pis in the field through secure shell (S S H) via putty after the Hologram SpaceBridge linked the Pi to a local port on the laptop. Three main Python programs were run constantly over the experimental period to enable the remote control and analysis. On the control Pi, a program was run to launch the irrigation and monitor the time span during each scheduling. On the data Pi, one program was run to fetch various field data by serially communicating with the dataloggers. Another program was run to upload these data to Things Board in real time. This year, we no longer required in-field acquisition and manual uploading of any data type after the system was established, as compared in Figure two point eight. The Python codes are provided in Appendix five point three.

However, at current stage there is still human-in-the-loop to make decision on when and how much to irrigate. These decisions were made after a preliminary analysis of the S W P and weather data on the cloud. True automation can be achieved after we have a better understanding of the plant water response under different scenarios. Then, we can finalize the model of the tree to accurately inform irrigation decision.

Section three point three, Setup at the Cornell Orchard.

<break time="0.8s"/>

In addition to the irrigation control system, the following instruments were incorporated to conduct the apple control irrigation experiments in Summer two thousand twenty (Figure two point nine).

Four drippers (flow rate approximately zero point one six liters per minute) were inserted into each soil pot at a depth of roughly ten centimeters from the soil surface. Two soil stress sensors (WATERMARK two hundred Model two hundred fifty-three) were used to record the soil water potential at different depths of the respective pot, especially during irrigation events and dry-down period. In each pot, one soil sensor was installed with its center at ten centimeters deep and the other with its center at fifteen centimeters deep (Figure two point nine (a) & (b)). The installation of the soil sensors (Acknowledgement of Robert Schindelbeck for the soil equipment and assistance) were accomplished using a soil augur and the locations for installation were chosen to be representative of the surrounding soil-root interaction. The procedure includes: - Soak the soil sensors overnight and keep them in water before installation. - Drill a hole to the desired depth in the soil pot with a soil augar. - Mix the removed soil with water to make a slurry. - Install the soil sensor into the hole and fill the gap between the sensor and soil with the slurry.

One of the trees (T four ) was put on a digital scale (Figure two point nine (d)) for the entire time. The scale was used to provide an estimation of the irrigation and transpiration rate of the measured apple tree. The direct measurement of E T from the scale was compared with the modeled E T using Penman-Monteith equation (Equation one point eight).twenty-five, twenty-six We used a CR six datalogger with a multiplexer (Campbell Scientific) to read the data from the soil sensors and the scale.

Before the experiment started, we covered each pot with a waterproof board to minimize evaporation from the soil surface. One micro-tensiometer was instrumented into the trunk of each tree using the previously discussed embedding technique to record the dynamic water stress over the experimental period. We used another set of a CR six and a multiplexer to record the microtensiometer data every minute.

A micro-climate station (Figure two point nine (e)) measured windspeed (C two one nine two ), relative humidity and room temperature (HMP-sixty, Vaisala), solar radiation (L I two hundred R, L I C O R), and photosynthetically active radiation (L I one hundred ninety-three, L I C O R) around the potted apple trees was mounted on the experimental set. We used a third CR six datalogger to read these measurements every minute. All the field data were also stored locally on the data Pi (Figure two point nine (c)) and online via Things Board.

Section four, Comparison between Measured and Modeled E T.

<break time="0.8s"/>

The scale-measured E T is compared with the PM-predicted E T (Equation one point eight) in Figure two point ten. Due to frequent wind disturbances in the field, the directly recorded E T by the digital scale (E T scale) appears noisy. Nonetheless, E T scale serves as an important comparison for validating the modeled E T Penman-Monteith that facilitates accurate modeling of the S W P.

In addition, Figure two point eleven shows the cumulative E T, in kilograms, over this period by integrating the measured and modelled E T in Figure two point ten with respect to time. The cumulative modelled E T agrees relatively well with the cumulative measured E T except at the beginning (from Sept. fifteenth to sixteenth). This is possibly due to the scale measurement error as the scale experiences frequent wind disturbances. In general, the model prediction falls slightly below the scale measurement after Sept. sixteenth. This might indicate a potential underestimation of E T predicted by the PM model. For instance, on the nights of Sept. sixteenth, twenty-third and twenty-fourth in particular (Figure two point ten), the nighttime transpiration is not well captured by the PM model. As a result, the predicted E T, in kilograms per second, was much smaller compared to the measured E T during these nights. These differences are cumulative over time that could yield overall smaller modelled cumulative E T. This phenomenon is worth further investigation to determine the proper nighttime stomatal opening to allow higher nighttime transpiration.

Section five, Comparison between micro-tensiometer and S P C Measurements.

<break time="0.8s"/>

The start date of the experiments was Sept. two nd, two thousand twenty when the micro-tensiometer installed in T two ( mu TM two ) functioned stably. The validity of the micro-tensiometer was justified by comparing its measurements with the Scholander Pressure Chamber (S P C) measurements. A diurnal of hourly S P C measurements (Acknowledgement of Dr. Annika Huber for the measurements) was conducted on Sept. eleven th after Tree one was also instrumented ( mu TM one ), as shown in Figure two point twelve where the last date presented was arbitrarily chosen to be Sept. nineteen th.

mu TM one (Figure two point twelve (a)) shows a good agreement with the S P C measurements on T one. Yet quite surprisingly, mu TM two (Figure two point twelve (b)) shows little agreement with the S P C measurements on T two. There are three potential reasons to rationalize the disagreement exhibited in T two measurements. Firstly, the measurements were taken at almost the end of the growing season when the trees were likely to behave not as usual. Right around the day that the S P C measurements were conducted, the diurnal magnitude of S W P changed considerably that can be clearly identified from Figure two point twelve (b). This drop in diurnal magnitude signified the onset of defoliation stage. In addition, T two had the most fruit load that might impact the S W P, which will be further illustrated in next chapter. Lastly, T two S P C measurements were almost twice as negative compared with those from T one and T four (not presented) on Sept. eleven th, a supposedly low-stress day as the sun was covered till three pm.

Nevertheless, because of the disagreement experienced by T two, T one data will be used for analysis over the dry-down cycle (Chapter three) for refining the water-stressed apple model. However, before Sept. eleven th, mu TM two showed reasonable diurnal S W P variation and followed V P D closely. Therefore, T two data will still be used, mainly for analysis before the dry-down cycle and for tuning the parameters in the well-watered apple model.

Section six, Conclusion.

<break time="0.8s"/>

In this chapter, the fabrication, characterization, and installation of the micro-tensiometer were presented. Additionally, the field setup integrating the micro-tensiometer and other ground-truth sensing in an irrigation control framework were described and the experimental results will be discussed in detail in Chapter three. Lastly, the methods for S P A C modelling (Chapter two Section two point two) were compared with the experimental data. We concluded that we can infer the interaction between the tree and the atmosphere (as variations in the evaporative demands) using the Penman-Monteith equation as Figure two point ten presents. We also confirmed that generally the micro-tensiometer was able to achieve a linear relationship with the widely acknowledged Scholander Pressure Chamber (S P C) measurements during in-plant testing (Figure two point twelve (a)). The deviation of the micro-tensiometer from the S P C data (Figure two point twelve (b)) motivates study relating the fruit quality and stem water potential and will be further discussed in the next chapter.

Chapter three. RESULTS AND DISCUSSION.

<break time="0.8s"/>

Section one, Plant Response to Controlled Irrigation Experiments.

<break time="0.8s"/>

A good understanding of how the plant responds to water stress is necessary to portray the full dynamics of plant water response that could potentially aid the implementation of effective control strategies. A phenomenon was observed that S W P followed E T nicely but did not respond to small watering events during daytime in Summer two thousand nineteen, as shown in Figure three point one. The plant was more responsive to nighttime irrigation as seen in the relaxation of stress. As a result, the Summer two thousand twenty experiments served as a continuation of Summer two thousand nineteen experiments to further examine the responses of S W P to irrigation events under varying evaporative demands.

In the Summer two thousand twenty experiments, we aimed to further study the impacts of irrigation mode, amount, and timing on plant water response to evaluate the relative value of launching irrigation at night or predawn for better root water uptake. The irrigation mode was compared between the drip irrigation via emitters as in our current setup and flood irrigation when we manually fertigated the trees. The irrigation amount was defined by comparing with the cumulative evapotranspiration (E T) on full-sun days. As a rough estimate, the potted apple trees at their current phenological stage should receive two point five to three L water daily on a typical sunny day during summer. This estimation is also confirmed by the measured E T (Figure two point eleven).

During daytime, the irrigation timing was chosen either to be when the S W P started developing stress (mid-morning: around ten am) or the S W P reached the most negative value (midday: normally around three to five pm). At night, the timing was chosen when the stem was fully relaxed (nighttime: after nine pm).

Over the summer, we used the irrigation system (Chapter two Sections three point two & three point three) to maintain the trees hydrated; we will refer to this as well-watered state. Then we withheld water to develop drought stress to witness the dry-down and rehydration pattern; we will refer to these as dry-down cycles.

Figures three point two and three point three present the full dynamics over the experimental period for T one and T two, respectively. The estimated transpiration (E T) and soil water potential are also presented as they are the main determinants of plant water stress.

Section one point one, Well-watered State.

<break time="0.8s"/>

In Figure three point four (a), we present the stem water potential measurements by the mu TM and the modeled stem and soil water potentials from the two-compartment model (Chapter one Section two point two point four) together with daily irrigation events. When the apple trees received sufficient daily irrigation to compensate their water loss through E T, the plants can be considered well-watered. Therefore, before Sept. seventeen th, the trees were at well-watered state: the predawn stem water potential returned to a similar baseline every day ( predawn water potential of order zero point four megapascals). In this well-watered state, the soil can be considered saturated so the soil hydraulic resistance ( R s) was negligible. The trunk resistance ( R t) and capacitance ( C t) were tuned within expected ranges. Importantly, the plant compartment in the model captures the measured stem water potential relatively well with reasonable hydraulic parameters (Table three point one) as justified by Figure three point four (b). Figure three point four (b) presents the residual calculated from the difference between the measurement and the model, and is negligible for most of the presented period. Additionally, Figure three point four (c) shows the prediction of E T using the Penman-Monteith equation (Equation one point eight) with the collected local meteorological variables (Figure three point four (d) v wind and (e) P A R). Further, we estimated V P D (Figure three point four (f)) using Equations one point four and one point five.

Table three point one summarizes the parameters used in the model and detail can be retrieved from Chapter one Section two point two point four.

Table two. This table lists the hydraulic parameters used in the model, including the transport and capacitance values for the soil and root components, along with their governing equations and units expressed in terms of pressure, time, and mass.

Similar to observations in Summer two thousand nineteen: under well-watered state, SWP did not show clear responses to irrigation launched during daytime. Nonetheless, both the measured and modelled SWP more directly responded to nighttime irrigation by continuing relaxing stress after the onset of irrigation to maintain the tree well-watered. The model started failing right before the dry-down period when it no longer sensed irrigation and the soil became unsaturated, resulting in ever increasing residual (Figure three point four (b)). We will return to this discrepancy after further refining the soil compartment.

Further, Figure three point five provides a zoom-in dynamics of S W P responses, displayed together with the estimated E T and measured environmental variables, on a typical day during the well-watered state. On Sept. ten th, both drip irrigation (two point five L at seven:thirty am) and flood fertigation (two L at seven:thirty pm) were conducted. The fertigation (also referred to as flood irrigation later) was applied by manually flooding the fertilizer after the pot cover (Figure two point nine (a)) was temporarily removed. However, neither event seemed to trigger direct response of S W P. S W P closely followed variations in E T, driven by solar radiation (during daytime), wind speed and most importantly, V P D. As the day proceeded, S W P continued to develop stress and tended to relax only after E T started dropping after midday.

We expected the micro-tensiometer measurements to show a difference in S W P responses to the two different modes of irrigation. For instance, the flood irrigation could trigger response in shorter time, despite the fact that the timing of irrigation had changed between the events (i.e. the first event was issued in the morning and the second at night). However, as mentioned previously, in reality no substantial relaxation of stem was observed upon irrigation especially during daytime. Further, it is uncertain that the fertigation directly led to the relaxation of S W P as E T was slowly approaching zero around the same time, thus decreasing the driving force to stress the stem. Besides, the fertigation could create an osmotic potential around the roots due to the solutes in the water. We need to account for this difference in future experiments that will be elucidated in Chapter four Section two. Lastly, the fact that neither the modeled soil nor the modeled stem experienced substantial relaxation in water potential ( delta psi) calls for further investigation of current model structure. It might indicate, for instance, the chosen hydraulic resistances are too large so the model is not sensitive to irrigation. We will also further the model refinement from this end.

Section one point two, First Dry-down Cycle.

<break time="0.8s"/>

Figure three point six (a) shows the measured and modeled (simulated with Equations one point six and one point seven) S W P responses during a dry-down cycle. From Sep. seventeen th to twenty-three rd, we withheld water from the potted apple trees to generate drought stress and then explored the impact of different re-watering timing on plant responses. As the water stored in the soil was depleted slowly, the plant entered waterstressed condition as the plant can longer relay on soil water to maintain well-watered. The trend of descending midday S W P over the dry-down cycle indicated the development of plant drought stress (due to persistent water deficiency) from its well-watered state gradually towards severe stress, a level of water stress that could induce cavitation in the xylem to reduce the plant's capacity of water transport. It is worth stressing that the magnitudes of the environmental driving forces (v wind, P A R, V P D as shown in Figure three point six (e), (f), (g), respectively) were comparable during this period. We therefore conclude that the observed decrease in the measured S W P was a direct response to soil depletion.

The measured and modeled dynamics of S W P follow same trend of dehydration, driven by both the evaporative demand (Figure three point six (d)) and soil dehydration (Figure three point six (c)). However as Figure three point six (b) presents, the residual (R E S) becomes large as dehydration proceeds, partly due to a loss of synchronization between the model and the measurement during this period. The current two-compartment model is not refined, possibly due to the challenges associated with the soil compartment as when the soil dehydration is negligible (at well-watered state shown in Figure three point four (a)), the modeled plant compartment agrees with the measurement relatively well. As drought stress is developed, the modelled S W P shows a phase lag and less responsiveness towards high frequency environmental signals compared to the measured S W P. Consequently, the model appears to filter out some dynamics and therefore results in a much smoother shape. For instance, the model does not capture the mid-afternoon relaxation in S W P from Sept. nineteen th to twenty-two nd (Figure three point six (a)). In summary, we identified two major discrepancies between the current model and the measurement. We discuss each in detail as follows.

Firstly, Figure three point six (a) shows mid-afternoon rises in the S W P measurement, not reflected by the model. These seemingly odd relaxations may be responses to very localized and temporary changes in sky coverage. However, only variations in the original P A R data can be possibly related to these responses; none of the other environmental driving forces show mid-afternoon variations over the period. We noted that the original P A R measurements during these days exhibited midafternoon drops and could be associated with the corresponding rises in S W P. We thus compared the P A R data with that posted by the local weather station (Network for Environment and Weather Applications (N E W A)) and observed no oddity from the weather station data. In addition, the measured air temperature (T) from our local microclimate station also exhibited no mid-afternoon drops so the estimated V P D (Figure three point six (g)) was not affected. V P D would also be affected when there was an impact on P A R as both are sensitive to temperature variations. We therefore concluded that the observed mid-afternoon drops in the P A R data were unlikely to be physical. Rather, they were more likely to be due to electronics interference as the P A R sensor is very sensitive. We thus performed a linear interpolation to smooth the P A R data (Figure three point six (f)) over the period.

Besides, the delay in the model could emerge when the time constant, tau, (i.e. the product of R and C) in either the plant or the soil compartment is too significant in a RC circuit. As dehydration proceeds, the soil resistance, for instance, is no longer negligible. The model therefore possesses more complex time constants that could drive the model out of phase, resulting in increasing R E S (Figure three point six (b)). The largest R E S occurred on the day of re-watering (Sept. twenty-three rd) as the time lag between the model and the measurement became most significant. This significant R E S indicates the necessity to further refine the two-compartment model, either through building a more complex RC correlation or taking a closer look into root morphology. For instance, the roots can induce substantial change of the soil water retention properties. The root exudates, gel-like substances secreted by the roots that influence the rye-zo-sphere, can play key roles in plant drought response. The root exudates could serve as stress mediators as the dehydration of the exudates could yield a hydrophobic layer surrounding the roots and thus prevent them from further losing water to the excessively dried soil.

On Sept. twenty-three rd, the predawn stem water potential no longer returned to baseline, indicating further depletion of the water stored in soil. we also observed this trend from the direct measurement of soil water potential, soil water potential, in Figure three point six (c). Sept. twenty-three rd also witnessed the largest amplitude of diurnal variation in measured S W P. Noticeably, even at its most stressed state, soil water potential remained above zero point one megapascals, incomparable to the minus four point two megapascals experienced by the stem (Figure three point six (a)). Therefore, the plant can develop significant drought stress not tracked by soil sensing, further challenging the reliability of basing precision irrigation decision on soil measurements.

We now turn to analyze the performance of the current model. To capture the dry-down dynamics measured by the micro-tensiometer, we tuned the parameters of resistances and capacitances, within expected range, to achieve the desired trend. The selection of initial values was discussed in Chapter one Section two point two point four and summarized in Table three point one. For the plant compartment, we adopted the same constant R t and C t based on the assumption of no cavitation in the xylem tissues under the studied stress level. For the soil compartment, the water retention parameters (n, m, theta s, theta r, K s,sat) directly affect the resistances and capacitances of this compartment and were adjusted based on literature values for sand, the soil media for the potted apple trees used.

Figure three point seven compares the hydraulic resistances in the two-compartment model for capturing the dry-down cycle in Figure three point six (a). As mentioned previously, the trunk resistance was kept constant. During this period, significant increases in the soil resistance and rye-zo-sphere resistance (rhizosphere resistance) were predicted. In Figure three point seven, R r increased slowly in response to the development of plant drought stress, even though R r remained the largest by magnitude. The nonlinearity in the soil properties was reflected by the rapid increase in R S as psi s decreased below the air entry potential (defined by alpha s). R s varied by orders of magnitude, reaching to a significant value on the most stressed day and then decreasing rapidly in response to rehydration; R s showed the highest sensitivity to irrigation events. Additionally, in the current model, R s did not surpass R t even on the most stressed day.

We present yet a primitive attempt to capture the dry-down cycle and following rehydration for Summer two thousand twenty data. Fundamentally, the current two-compartment model does not closely agree with the actual plant in responding to rehydration. We will focus on studying the soil retention properties to further refine and mature the model.

Therefore, we now take a close look at the rehydration dynamics, as shown in Figure three point eight (a). We aimed to test the sensitivity of S W P to irrigation after a severe drought stress by investigating how much would the trees respond within a certain time period (set arbitrarily for thirty mins). As a result, two L water via drip irrigation was issued per tree around midday, which was three pm on Sept. twenty-three rd. We found both the model and the measurement recovered at similar rate. In addition, this recovery of S W P was relatively fast as the trees showed strong responses to irrigation by rehydrating from minus two point two megapascals to minus two point zero megapascals in thirty mins upon irrigation while the E T (Figure three point eight (c)) remained constant at its daily maximum and V P D kept ramping up (Figure three point eight (e)).

Following Sept. twenty-three rd, different irrigation timing was tested on a daily basis to examine the impact on S W P responses. Also shown in Figure three point eight (a), the S W P was able to relax back to its baseline value on Sept. twenty-four th within one day after irrigation was resumed. Additionally, Figure three point eight (b) indicates that the soil rehydration occurred first as a step change in the top (ten cm depth) and then slower in the bottom (fifteen cm depth) of the soil pot.

We tested drip irrigation at (one) ten am on Sept. twenty-four th when E T and V P D were marching towards their daily maximum, (two) five pm on Sept. twenty-five th when E T and V P D were stabilizing around their daily maximum, and (three) nine pm on Sept. twenty-six th when E T and V P D were plateauing towards their daily minimum. We found that S W P clearly responded to irrigation events by relaxing the stress and not continuing following variations in the evaporative demand within thirty mins onset of irrigation under both (one) and (two). The response in (three) was difficult to identify given that the stem was already relaxed at that time.

In summary, the micro-tensiometer saw clear responses of the stem to midmorning and midday watering events after the dry-down cycle. This daytime responsiveness was not observed in the previous year. Due to the observed differences in S W P responses after a dry-down cycle, a second development of drought stress was attempted and featured on exploring S W P responses to small re-watering events during daytime, as presented in Chapter three Section one point three.

Additionally, to further illustrate the disconnection between the soil and the plant during the first dry-down, we plotted the measured soil and stem water potentials together (Figure three point nine (b)) and compared with the theoretical dehydration process (Figure three point nine (a)). Although Slatyer and Cowan acknowledged disequilibrium; they indicated the occurrence of disequilibrium at a much lower soil water potential (minus one point five megapascals) than what we observed. We discovered persistent disequilibrium between the soil and the plant even at well-watered state that challenges the theory prediction. This decoupling between the soil and the plant compartments could provide insights for the refinement of our S P A C model, as will be illustrated in Chapter four Section one.

Section one point three, Second Dry-down Cycle.

<break time="0.8s"/>

From Oct. first to seventh, we withheld water from the potted apple trees to generate drought stress for a second time. Figure three point ten (a) shows the measured and modeled S W P during this period. On Oct. seven th, the predawn stem water potential showed evident deviation from its usual baseline, signifying the onset of soil depletion that was also identified from the drop in measured soil water potentials as shown in Figure three point ten (b).

Due to the fact that the experimental time was already at late fall and the trees had started losing leaves around the end of September, the drought stress developed this time was moderate with lowest S W P around minus two megapascals as shown in Figure three point ten (a). Figure three point ten (c) indicates the daily E T lowered as compared to that in the first dry-down cycle (Figure three point six (d)). This is because the trees no longer had high demand of water due to the reduced leaf area. Consequently, we changed the total daily irrigation amount to one L to avoid overwatering and also to further test the sensitivity of S W P to small irrigation events. More specifically, for the rehydration after the second dry-down, each irrigation event supplied zero point five L water and we issued twice per day at different timing. zero point five L irrigation can be considered as a "small" watering event compared to the two L routine during our previous dry-down cycle. We aimed to test the response of S W P to deficit irrigation during daytime when the soil-root connection might be less intact and root water uptake less effective.

Similar to that in the first dry-down cycle, the prediction of S W P on the most stressed day (Oct. seven th in the second dry-down) was much lower compared to the measurement. One possibility would be that in reality the root exudates play important roles in facilitating plant drought response. The dehydration of the exudates could yield a hydrophobic layer surrounding the roots and thus prevent them from further losing water and developing excessive stress.

Further, after rehydration, the recovery of measured soil water potential at different depth of the pot (ten cm and fifteen cm) occurred at different time. This is possibly due to either the different root architecture at different soil depth or the time required for water to percolate through the soil column as it is added from the top. More importantly, this recovery in the soil is different from that observed in the first dry-down cycle (Figure three point six (c)). In addition, during the second dry-down, S W P seemed to recovery completely after rehydration whereas neither soil layer did. Both are worth further investigation to refine the soil compartment of our S P A C model.

A zoom-in of the first rehydration event, scheduled at three pm, on Oct. seven th is provided in Figure three point eleven. S W P followed E T closely as S W P continued to drop in response to increasing E T after three pm. Interestingly, however, around thirty mins upon irrigation, S W P relaxed before V P D started to decrease (due to precipitation around three:forty pm). This increase in S W P could be a response to both irrigation and decreasing V P D, suggesting the possibility of S W P responding to small irrigation event during daytime. Looking closer at the period after sunset (six to eight pm), a prolonged and more significant rehydration to the three pm irrigation event was observed. The stem further relaxed while V P D was slowing rising around the same time. An additional zero point five L irrigation was issued at nine pm when the V P D was slowly flattening. S W P kept increasing, possibly in response to the combined effects of rewatering and nighttime relaxation due to decreasing V P D. Both irrigation events confirmed more effective root water uptake at night as the S W P response was more immediate to nighttime watering.

Additionally, the apples were harvested on the night of Oct. seven th to examine roughly the impact of fruit load on S W P. As Figure three point twelve (a) shows, psi mu T M exhibited evident relaxation in predawn S W P in the following two days. The evaporative demands from Oct. eight th - nine th were comparable to those back on Oct. four th - five th, yet a baseline shift of predawn S W P was observed, suggesting a correlation between the fruit load and S W P that calls for future investigation. This potential impact of fruit load lowering the S W P could also rationalize the observed discrepancy in measurements from a micro-tensiometer and a S P C shown in Figure two point twelve (b). The apples could act as evaporating sites, similar to the leaves, and generate additional sink for water transport along S P A C. T two had the most fruit load and its water status could therefore be affected the most.

Following Oct. seven th, different small irrigation events were attempted to investigate the impact of the amount of irrigation, when combined with timing, on S W P responses in fluctuating environment, as highlighted in Figure three point twelve. As mentioned previously, each irrigation event issued zero point five L water, equivalent to three mins of irrigation. The micro-tensiometer seemed to be able to identify these events by looking at the measured S W P variations soon upon irrigation. Although the impact of varying E T on S W P responses can not be clearly decoupled this time, S W P still showed some sensitivity towards irrigation that was not perceived last year. In particular, S W P seemingly relaxed after one hr of midmorning (ten am) irrigation while E T continued increasing on both Oct. eleven th and twelve th.

The observed difference in S W P responses to daytime irrigation events between Summer two thousand twenty and Summer two thousand nineteen might be rationalized as follows: Firstly, the irrigation was issued intermittently (i.e. the valves were programmed to alternate between on and off so the delivery of water was noncontinuous) in Summer two thousand nineteen but continuously (i.e. the valves were kept on until the total desired amount of water was delivered) in Summer two thousand twenty. Though both modes of delivery were through the same drippers, the continuous approach this year might be more similar to flood irrigation that can temporarily saturate the soil to facilitate plant response. In addition, there might be droughtinduced changes in the root system that can explain the seemingly responsiveness when coupled with seasonal phenology.

The launch date of Summer two thousand twenty was more than half month later compared to that in the previous year, therefore the fruit were already mature. Although it is known that apple tree roots do not grow during summer as they are occupied with delivery of water and nutrients to mature the fruit, the fibrous roots start to grow when fall encounters as the apple are mature. Fine roots developed from the fibrous roots can take up water from soil near the surface.

Further, it is also possible that the roots can uptake water during daytime but can not effectively rehydrate the plant due to the root shrinkage in response to evaporative loss. Consequently, the timescale for roots to respond to an irrigation event varies between during the day and at night, resulting in daytime S W P non-responsiveness to external watering during growing season as observed last year. However, the growth of fibrous roots at the end of the growing season can facilitate the water transport and possibly lower the barrier for daytime rehydration as observed this year. Yet, whether it is the drought-induced root growth that facilitates water uptake requires future investigation by carrying out the experiments throughout different phenological stages (growing season, harvest, defoliation) next year, which will be discussed in Chapter four Section two point two.

Chapter four. FUTURE WORK AND CONCLUSION.

<break time="0.8s"/>

Section one, Simulation: Model the Potted Apple Trees under Water Stress.

<break time="0.8s"/>

Section one point one, Stratify the Soil Compartment into Two Layers.

<break time="0.8s"/>

Soil dehydration directly leads to plants' experience of severe drought stress. To better understand this dynamics and refine our S P A C model, we require an accurate soil compartment in addition to the plant compartment.

As shown previously in Figure three point ten (b), the recovery of soil stress in response to irrigation exhibited a time lag between different depth of the pot. It is therefore worth stratifying the bulk soil into two layers and compare the predictions for each layer with the direct soil sensor measurements, as proposed in Figure four point one.

The construction of the soil compartment will follow Equations four point one and four point two:

Equation four point one.

Equation four point two.

where C s zero and R s zero are the soil hydraulic capacitance and resistance, respectively, defining the upper soil compartment; and C s one and R s one define the lower soil compartment. Both the soil capacitances and resistances depend on the soil water potentials through the respective compartment ( psi s zero for the top layer and psi s one for the bottom layer). The soil water potential at the bottom of the soil pot is arbitrarily set to zero with the assumption that excessive irrigation gets drained to the bottom and saturates the bottom portion of the soil.

Section one point two, Incorporate Mechanistic Stomatal Regulation.

<break time="0.8s"/>

The opening and closing of stomata directly control the rate of E T at given stem water potential, V P D and solar intensity. An appropriate mechanistic model for the stomata is therefore important in enhancing the current understanding of plant drought response. As the experiments in Summer two thousand twenty were launched later compared to those in the previous years, differences in measured S W P when the environmental driving forces were comparable can be used to explore the regulatory role of the stomata at different phenological stages, further extending the applicability of the current models.

Section two, Experiment: Continue Exploration of Apple Stress Physiology.

<break time="0.8s"/>

Section two point one, Experiment across Different Seasonal Phenology.

<break time="0.8s"/>

For the field experiment in the coming year, the mu TMs will be installed at the beginning of the growing season and their measurements will span the growing season, harvest and defoliation stages to examine the changes in diurnal variations across different phenological stages.

In addition, the experimental trees will be separated into a control group and an irrigation group to better explore which timing of irrigation in a diurnal has the strongest effect on S W P. At harvest, another comparison experiment can be set to remove apples from some of the trees to further investigate the correlation between fruit load and S W P.

Section two point two, Experiment with Different Rootstocks.

<break time="0.8s"/>

As different rootstocks exhibit different root water uptake patterns, it is also worth including trees of different rootstocks in the coming year. Within each tree, two mu TMs could be embedded, as overviewed in Figure four point two. By comparing whether the two mu TMs show considerable difference in measurements, we can further explore the water storing capacity of the root. For instance, if the micro-tensiometer near the surface root shows a higher water potential compared to the micro-tensiometer in the main trunk, we can further investigate the role of the roots in storing water that could lead further refinement of the model architecture.

Lastly, we will also attempt direct monitoring of some leaf functions such as the leaf transpiration and stomatal conductance next year that can be combined with the in-plant sensing of the micro-tensiometer and the soil sensing to complete the experimental construction of the S P A C.

Section three, System: Improve the Irrigation System for Scalable In-field Deployment.

<break time="0.8s"/>

Section three point one, Refine the Power Supply and Integrate with Cloud Interface.

<break time="0.8s"/>

To deploy at scale, the current setup needs to be further improved. Firstly, the current setup is site-specific as it relies purely on power drawn from the site. To move to the next stage, we need to get rid of this dependence on field power, possibly by rationalizing the use of solar panels. We will work on incorporating more solar panels, mounted at an angle to capture the maximum sunlight, and backup batteries to ensure sufficient power for the hardware to operate at night and during sustained rainy period. In addition, relying on three G dongle in the field to control irrigation and upload data is costly and sometimes unstable. A transformation to wireless connectivity, such as TV White Spaces (T V W S), is an important next step. Lastly, we currently still use commercial dataloggers for all the sensing, which restrict the layout design with the availability of connected wires. When we scale up the current design and space each tree further apart from its neighbor, we will need to extend the wirings from the embedded micro-tensiometer to the datalogger. The crossing of wires could pose potential trip hazard and disarrange the system. Therefore, individual datalogger will be necessary to add flexibility and accessibility to the site layout.

We will continue seeking collaboration with electrical and computing experts to further this front, deploying the irrigation control system at scale as portrayed in Figure four point three.

Section three point two, Determine the Density of micro-tensiometer Installation.

<break time="0.8s"/>

Sensing on every plant in a field using a micro-tensiometer is burdensome and economically not viable, whereas relying fully on remote sensing (a tool that can capture the spatial heterogeneity) and crop models do not provide sufficient and accurate enough information to estimate in-plant water status as the models can have accumulation of errors. Besides, remotely sensed variables typically provide static information that is not proper for irrigation management.

Therefore, after further refining the plant-scale models, we will deploy the in-plant sensing and irrigation system at scale by instrumenting more controlled plants to have a better understanding of the heterogeneity in weather, soil and plant water relations. Then, we aim to rudimentarily upscale the models to suit for a collection of apple trees. By comparing the difference between collected field data from extensive embedding and model estimation of S W P, we will get an idea of the size of a block in which plants share similar water relations that are sufficiently representative by one micro-tensiometer installation. We can then determine the minimum density of on-site installation.

In long run, we can have minimal ground-truthing instruments. As an illustration, in each row of the crops shown in Figure four point three, one sensor can be installed to continuously monitor S W P. This sentinel plant is coupled with accurate control algorithms which account for weather and other factors such as water availability to optimize the irrigation decision, sending real-time measurement information and irrigation recommendations to its users.

Section four, Conclusion.

<break time="0.8s"/>

The use of the micro-tensiometer as a tool to instruct irrigation management in experimental settings was presented in this thesis. The micro-tensiometer has been testified to be able to measure the plant stem water potential accurately, continuously and minimally destructively.

The field experiments in Summer two thousand twenty were aimed to continue the exploration of plant water responses to well-controlled irrigation events, which lays the foundation for constructing a robust model for model predictive control (M P C) based on the micro-tensiometer to enhance irrigation management.

In particular, we studied the impact of timing and amount, when coupled with timing, of irrigation on plant drought responses after dry-down cycles. As a conclusion, we confirmed that the roots exhibit different response timescales to rehydration and the timescale of transient water uptake has direct correlation with the drought stress level at the root-zone. At night, the stem relaxes as the environmental driving forces flatten. The relaxed roots more effectively uptake water and rehydrate the plant by showing faster response to same amount of irrigation compared to that during daytime. However, the trees show clear responses to midmorning and midday irrigation after a dry-down cycle when they have developed severe drought stress. This responsiveness in S W P when the trees are actively transpiring was not observed in previous studies. One potential cause would be the root growth after growing season facilitates the water uptake. Further investigation and future experiments that span different seasonal phenology will help to validate this hypothesis.

Additionally, we identified that the dynamic responses of the plants to stress and rehydration are best reflected by stem water potential measurements. The developed stress in the soil is insignificant compared to that in plant when severe drought stress is encountered. Consequently, soil sensing can not entail the real stress experienced by the plant and therefore can not properly inform precision irrigation. Further characterization of different irrigation strategies will be conducted in the following growing seasons for continued study on drought-induced stress physiology.

Relating to previous studies, we further confirmed that we can infer the hydraulic properties of the plant, including its interaction with the atmosphere, under well-watered regime. The Summer two thousand twenty experiments imply open opportunities for using the stem water potential to inform the properties of the soil and the rye-zo-sphere that calls for continued study.

In the end, the instrumented micro-tensiometer along with the developed hydraulic models of the plant, when integrated in a well-defined control framework, can achieve unprecedented maintenance of plant water status at different plant phenological stages. This fine control will give growers confidence that precision irrigation can be realized without compromising crop productivity, thereby reconciling the challenge of feeding a growing world with endangered water resource.

This concludes Study of in-plant sensing for the precise control of water use in agriculture.